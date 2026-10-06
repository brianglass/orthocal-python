import asyncio
import contextlib
import io
import json

from unittest import IsolatedAsyncioTestCase, mock

from .. import request_log


def _scope(method='POST', headers=()):
    return {
        'type': 'http',
        'method': method,
        'path': '/mcp',
        'headers': [(k.encode(), v.encode()) for k, v in headers],
    }


def _receiver(*chunks):
    messages = [
        {'type': 'http.request', 'body': chunk, 'more_body': i < len(chunks) - 1}
        for i, chunk in enumerate(chunks)
    ]

    async def receive():
        return messages.pop(0) if messages else {'type': 'http.disconnect'}

    return receive


async def _noop_send(message):
    pass


async def _echo_app(scope, receive, send):
    body = b''
    while True:
        message = await receive()
        body += message.get('body', b'')
        if not message.get('more_body'):
            break
    await send({'type': 'http.response.start', 'status': 200, 'headers': []})
    await send({'type': 'http.response.body', 'body': b'{"ok":true}'})


async def _run(app, scope, receive):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        await request_log.log_mcp_requests(app)(scope, receive, _noop_send)
    return [json.loads(line) for line in out.getvalue().splitlines()]


class LogMCPRequestsTestCase(IsolatedAsyncioTestCase):
    async def test_logs_method_and_timings_without_argument_values(self):
        body = json.dumps({
            'jsonrpc': '2.0', 'id': 7, 'method': 'tools/call',
            'params': {'name': 'search_saints', 'arguments': {'query': 'secret text'}, '_meta': {'progressToken': 7}},
        }).encode()
        scope = _scope(headers=[
            ('Accept', 'application/json, text/event-stream'),
            ('MCP-Protocol-Version', '2025-06-18'),
            ('X-Cloud-Trace-Context', 'abc123/456;o=1'),
            ('Authorization', 'Bearer xyz'),
        ])

        records = await _run(_echo_app, scope, _receiver(body[:10], body[10:]))

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record['stage'], 'done')
        self.assertEqual(record['trace_id'], 'abc123')
        self.assertEqual(record['status'], 200)
        self.assertEqual(record['body_bytes'], len(body))
        self.assertEqual(record['jsonrpc']['method'], 'tools/call')
        self.assertEqual(record['jsonrpc']['tool'], 'search_saints')
        self.assertEqual(record['jsonrpc']['meta_keys'], ['progressToken'])
        self.assertEqual(record['headers']['mcp-protocol-version'], '2025-06-18')
        self.assertEqual(record['has_headers'], ['authorization'])
        for key in ('body_complete_ms', 'response_start_ms', 'response_complete_ms'):
            self.assertIn(key, record)
        self.assertNotIn('secret text', json.dumps(record))
        self.assertNotIn('xyz', json.dumps(record))

    async def test_slow_request_logs_a_snapshot_before_finishing(self):
        async def hanging_app(scope, receive, send):
            await receive()
            await asyncio.sleep(0.2)
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
            await send({'type': 'http.response.body', 'body': b'{}'})

        body = b'{"jsonrpc":"2.0","id":1,"method":"ping"}'
        with mock.patch.object(request_log, 'SLOW_AFTER_SECONDS', 0.05):
            records = await _run(hanging_app, _scope(), _receiver(body))

        self.assertEqual([r['stage'] for r in records], ['slow', 'done'])
        self.assertEqual(records[0]['jsonrpc']['method'], 'ping')
        self.assertIn('body_complete_ms', records[0])
        self.assertNotIn('response_start_ms', records[0])
        self.assertIn('response_start_ms', records[1])

    async def test_batch_and_unparseable_bodies(self):
        batch = b'[{"jsonrpc":"2.0","method":"notifications/initialized"},{"jsonrpc":"2.0","id":2,"method":"tools/list"}]'
        records = await _run(_echo_app, _scope(), _receiver(batch))
        self.assertEqual([m['method'] for m in records[0]['jsonrpc']['batch']], ['notifications/initialized', 'tools/list'])

        records = await _run(_echo_app, _scope(), _receiver(b'{"jsonrpc":'))
        self.assertEqual(records[0]['jsonrpc'], {'parse_error': True})

    async def test_exception_is_logged_and_reraised(self):
        async def failing_app(scope, receive, send):
            raise RuntimeError('boom')

        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(RuntimeError):
            await request_log.log_mcp_requests(failing_app)(_scope(), _receiver(b'{}'), _noop_send)

        self.assertEqual(json.loads(out.getvalue())['exception'], 'RuntimeError')

    async def test_non_post_requests_pass_through_unlogged(self):
        records = await _run(_echo_app, _scope(method='DELETE'), _receiver(b''))
        self.assertEqual(records, [])

        lifespan_called = []

        async def lifespan_app(scope, receive, send):
            lifespan_called.append(scope['type'])

        await request_log.log_mcp_requests(lifespan_app)({'type': 'lifespan'}, None, None)
        self.assertEqual(lifespan_called, ['lifespan'])

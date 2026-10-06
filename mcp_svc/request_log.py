"""Diagnostic logging around POST /mcp.

Claude clients' connections intermittently stall on one POST that Cloud
Run holds to its 20s request timeout, and Cloud Run's request log can't say
why: it records neither the JSON-RPC method nor where the time went. This
wraps the MCP app and logs, per POST, which JSON-RPC message it carried and
when the request body finished arriving, the response started, and the
response finished -- enough to tell a client that never finishes sending
from a handler that never answers from a response that never closes.

Only the method, id, and parameter *names* are logged, never argument
values, so no user query text ends up in the logs.
"""

import asyncio
import json
import sys
import time

# A request still running after this long gets a snapshot logged, since a
# request Cloud Run abandons at its timeout may never reach the final log
# line at all.
SLOW_AFTER_SECONDS = 5

# Enough for any real JSON-RPC message to these tools; bodies beyond this
# are counted but not parsed.
MAX_PARSED_BODY = 64 * 1024

LOGGED_HEADERS = (
    'accept',
    'content-type',
    'content-length',
    'transfer-encoding',
    'mcp-protocol-version',
    'user-agent',
)
PRESENCE_HEADERS = ('mcp-session-id', 'last-event-id', 'origin', 'authorization')


def _summarize_message(message):
    if not isinstance(message, dict):
        return {'type': type(message).__name__}

    params = message.get('params')
    summary = {
        'method': message.get('method'),
        'id': message.get('id'),
        'is_response': 'result' in message or 'error' in message,
    }
    if isinstance(params, dict):
        summary['param_keys'] = sorted(params)
        if isinstance(params.get('_meta'), dict):
            summary['meta_keys'] = sorted(params['_meta'])
        if 'name' in params:
            summary['tool'] = params['name']
    return summary


def summarize_body(body):
    """Describe a JSON-RPC body (one message or a batch) without its
    argument values."""

    try:
        parsed = json.loads(body)
    except ValueError:
        return {'parse_error': True}

    if isinstance(parsed, list):
        return {'batch': [_summarize_message(m) for m in parsed]}
    return _summarize_message(parsed)


class _RequestRecord:
    def __init__(self, scope):
        headers = {k.decode('latin-1').lower(): v.decode('latin-1') for k, v in scope.get('headers', [])}

        self.started = time.monotonic()
        self.fields = {
            'mcp_request_log': True,
            'method': scope.get('method'),
            'headers': {h: headers[h] for h in LOGGED_HEADERS if h in headers},
            'has_headers': [h for h in PRESENCE_HEADERS if h in headers],
            'body_bytes': 0,
            'response_bytes': 0,
        }
        trace = headers.get('x-cloud-trace-context', '').split('/')[0]
        if trace:
            self.fields['trace_id'] = trace

        self.body = bytearray()

    def mark(self, event):
        self.fields.setdefault(f'{event}_ms', round((time.monotonic() - self.started) * 1000, 1))

    def emit(self, stage):
        # Parsed even before the body is complete, so a slow snapshot still
        # shows whatever arrived (as a parse_error if it's partial).
        if self.body:
            self.fields['jsonrpc'] = summarize_body(bytes(self.body))
        record = dict(self.fields, stage=stage, elapsed_ms=round((time.monotonic() - self.started) * 1000, 1))
        # Printed rather than sent through logging: Cloud Run only turns a
        # stdout line into a searchable jsonPayload when the whole line is
        # JSON, and settings.LOGGING's formatter prefixes the level name.
        print(json.dumps(record, default=str), file=sys.stdout, flush=True)


def log_mcp_requests(app):
    """Wrap an ASGI app, logging each POST it serves (see module doc)."""

    async def wrapped(scope, receive, send):
        if scope['type'] != 'http' or scope['method'] != 'POST':
            return await app(scope, receive, send)

        record = _RequestRecord(scope)

        async def logged_receive():
            message = await receive()
            if message['type'] == 'http.request':
                chunk = message.get('body', b'')
                record.fields['body_bytes'] += len(chunk)
                if len(record.body) < MAX_PARSED_BODY:
                    record.body += chunk
                if not message.get('more_body', False):
                    record.mark('body_complete')
            elif message['type'] == 'http.disconnect':
                record.mark('client_disconnect')
            return message

        async def logged_send(message):
            if message['type'] == 'http.response.start':
                record.fields['status'] = message['status']
                record.mark('response_start')
            elif message['type'] == 'http.response.body':
                record.fields['response_bytes'] += len(message.get('body', b''))
                if not message.get('more_body', False):
                    record.mark('response_complete')
            await send(message)

        async def watchdog():
            await asyncio.sleep(SLOW_AFTER_SECONDS)
            record.emit('slow')

        watchdog_task = asyncio.create_task(watchdog())
        try:
            await app(scope, logged_receive, logged_send)
        except BaseException as exc:
            record.fields['exception'] = type(exc).__name__
            raise
        finally:
            watchdog_task.cancel()
            record.emit('done')

    return wrapped

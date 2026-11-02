import asyncio
import gzip

import brotli

from django.test import SimpleTestCase

from .asgi import application


class CompressionTestCase(SimpleTestCase):
    """Responses are compressed in orthocal/asgi.py, outside Django."""

    async def get(self, accept_encoding):
        """GET /about/ through the whole ASGI application, and return the
        response headers and the body as sent, still compressed."""

        scope = {
            'type': 'http',
            'asgi': {'version': '3.0'},
            'http_version': '1.1',
            'method': 'GET',
            'scheme': 'http',
            'path': '/about/',
            'raw_path': b'/about/',
            'query_string': b'',
            'root_path': '',
            'headers': [(b'host', b'testserver'), (b'accept-encoding', accept_encoding.encode())],
            'client': ('127.0.0.1', 1234),
            'server': ('testserver', 80),
        }
        messages = []
        requests = [{'type': 'http.request', 'body': b'', 'more_body': False}]

        async def receive():
            if requests:
                return requests.pop()
            # The client stays connected; Django stops listening once it
            # has responded.
            await asyncio.Event().wait()

        async def send(message):
            messages.append(message)

        await application(scope, receive, send)

        start = messages[0]
        self.assertEqual(start['status'], 200)
        headers = {name.decode().lower(): value.decode() for name, value in start['headers']}
        body = b''.join(m.get('body', b'') for m in messages[1:] if m['type'] == 'http.response.body')
        return headers, body

    async def test_brotli_preferred(self):
        # What Chrome sends.
        headers, body = await self.get('gzip, deflate, br, zstd')

        self.assertEqual(headers['content-encoding'], 'br')
        self.assertIn('accept-encoding', headers['vary'].lower())
        self.assertIn(b'</html>', brotli.decompress(body))

    async def test_gzip(self):
        headers, body = await self.get('gzip, deflate')

        self.assertEqual(headers['content-encoding'], 'gzip')
        self.assertIn(b'</html>', gzip.decompress(body))

    async def test_no_zstd(self):
        headers, body = await self.get('zstd')

        self.assertNotIn('content-encoding', headers)
        self.assertIn(b'</html>', body)

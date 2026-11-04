import asyncio
import gzip

import brotli

from django.test import TestCase

from .asgi import application


class CompressionTestCase(TestCase):
    """Responses are compressed in orthocal/asgi.py, outside Django."""

    fixtures = ['calendarium.json', 'commemorations.json']

    async def get(self, accept_encoding, path='/about/'):
        """GET a path through the whole ASGI application, and return the
        response headers and the body as sent, still compressed."""

        scope = {
            'type': 'http',
            'asgi': {'version': '3.0'},
            'http_version': '1.1',
            'method': 'GET',
            'scheme': 'http',
            'path': path,
            'raw_path': path.encode(),
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
        html = brotli.decompress(body)
        self.assertIn(b'</html>', html)
        self.assertEqual(body, brotli.compress(html, quality=10))

    async def test_ical_quality(self):
        # The iCal feeds are large enough that quality 10 would be slow.
        headers, body = await self.get('gzip, deflate, br', '/api/gregorian/ical/')

        self.assertEqual(headers['content-encoding'], 'br')
        feed = brotli.decompress(body)
        self.assertIn(b'END:VCALENDAR', feed)
        self.assertEqual(body, brotli.compress(feed, quality=9))

    async def test_gzip(self):
        headers, body = await self.get('gzip, deflate')

        self.assertEqual(headers['content-encoding'], 'gzip')
        self.assertIn(b'</html>', gzip.decompress(body))

    async def test_no_zstd(self):
        headers, body = await self.get('zstd')

        self.assertNotIn('content-encoding', headers)
        self.assertIn(b'</html>', body)

from django.test import SimpleTestCase
from mcp.server.lowlevel.server import NotificationOptions
from mcp_types.version import MODERN_PROTOCOL_VERSIONS

from ..server import mcp


class ListenDisabledTestCase(SimpleTestCase):
    """server.py drops the subscriptions/listen handler through a private
    attribute (MCPServer has no option for it), so these fail loudly if an
    SDK upgrade moves it -- otherwise Claude clients would quietly go back
    to holding a 20s listen stream open on every connection."""

    def test_listen_is_not_served(self):
        self.assertIsNone(mcp._lowlevel_server.get_request_handler('subscriptions/listen'))

    def test_modern_capabilities_advertise_no_change_notifications(self):
        for version in MODERN_PROTOCOL_VERSIONS:
            capabilities = mcp._lowlevel_server.get_capabilities(
                NotificationOptions(), {}, protocol_version=version,
            )

            self.assertFalse(capabilities.tools.list_changed, version)
            self.assertFalse(capabilities.prompts.list_changed, version)
            self.assertFalse(capabilities.resources.list_changed, version)
            self.assertFalse(capabilities.resources.subscribe, version)

    def test_tools_are_still_served(self):
        self.assertIsNotNone(mcp._lowlevel_server.get_request_handler('tools/call'))

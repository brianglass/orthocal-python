from django.apps import AppConfig


class MCPSvcConfig(AppConfig):
    name = 'mcp_svc'

    def ready(self):
        # Importing this registers the tool functions onto the shared
        # MCPServer instance via their @mcp.tool() decorators.
        from . import tools  # noqa: F401

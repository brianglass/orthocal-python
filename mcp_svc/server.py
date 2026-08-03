from mcp.server.mcpserver import MCPServer

mcp = MCPServer(
    name='orthocal',
    instructions=(
        'Look up Eastern Orthodox liturgical calendar data: feasts, fasting '
        'rules, scripture readings, and lives of the saints for a given day, '
        'or search for a saint by name.'
    ),
)

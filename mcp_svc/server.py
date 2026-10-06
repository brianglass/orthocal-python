from mcp.server.mcpserver import MCPServer

mcp = MCPServer(
    name='orthocal',
    instructions='''\
Look up Eastern Orthodox liturgical calendar data: feasts, fasting rules,
scripture readings, and lives of the saints for a given day, or search for a
saint by name.

Choosing tradition and calendar:
- tradition=slavic follows OCA/ROCOR practice; tradition=greek follows Greek
  Orthodox (GOARCH) and Antiochian practice. Ask, or infer from the user's
  jurisdiction, when it matters -- feasts, readings, and fasting differ.
- calendar=gregorian is the New (Revised Julian) calendar; calendar=julian is
  the Old calendar used by ROCOR, most Slavic churches, Jerusalem, and Mount
  Athos. Greek-tradition users are almost always on the New calendar.

Dates:
- get_day always takes the civil (Gregorian) date the user is living on. With
  calendar=julian, the year/month/day in the result are the church-calendar
  (Julian) date, which is 13 days earlier -- e.g. civil January 7 returns
  December 25, the Nativity. Report the civil date to the user.
- search_saints returns the fixed church-calendar month/day of each
  commemoration. On the New calendar that is also the civil date. On the Old
  calendar, add 13 days to get the civil date (1900-2099) before calling
  get_day. Moveable feasts tied to Pascha are not found by search_saints.

Workflow: to tell someone about a saint, call search_saints, then get_day on
the resulting civil date for the full life (in stories) and the readings.

Reading results:
- summary_title is the best one-line name for the day.
- For fasting, combine fast_level_desc with fast_exception_desc, or use
  fast_abstentions for a plain list of foods to avoid. These reflect the
  strict typikon; suggest the user follow their parish or spiritual father's
  guidance on local practice.
- abbreviated_reading_indices picks out the main readings (usually the
  liturgy's Epistle and Gospel); use them for a short answer and the full
  readings list when asked for everything.
- Each reading's passage is a list of verses; stories are HTML, so strip
  markup when quoting them.
''',
)

# Don't serve subscriptions/listen (protocol 2026-07-28). It's a long-lived
# POST that waits to push change notifications, and orthocal never sends
# any -- its tools, prompts, and resources are fixed at deploy -- so Claude
# clients' listen streams sat idle until Cloud Run's 20s request timeout cut
# them off, then re-listened, each billed for the full 20s: the same problem
# asgi.py's _reject_get solves for the older GET stream. With no handler,
# server/discover advertises no listChanged or subscribe capability, so
# clients don't open the stream at all, and one that tries anyway gets an
# immediate "Method not found". MCPServer has no option to turn the handler
# off, hence reaching into the low-level server; test_server.py fails if an
# SDK upgrade changes this.
mcp._lowlevel_server._request_handlers.pop('subscriptions/listen', None)

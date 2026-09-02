# tools/oca

Harvesting and auditing against oca.org, the source the app's `common` and
`slavic` data was originally compiled from. Findings live in
`docs/oca-audit.md`; this file says which script produced what.

Read `docs/oca-audit.md` first if you are here to change something — it records
two traps in these pages that produced confidently wrong numbers.

| script | does |
|---|---|
| `fetch.py` | shared HTTP: on-disk cache, `Crawl-delay: 10`, the UA that works |
| `harvest_readings.py YEAR` | 12 monthly pages -> `data/oca_raw/readings-YYYY.json` |
| `harvest_saints.py YEAR` | 365 daily pages -> `data/oca_raw/saints-YYYY.json` (~1 hour) |
| `refs.py` | `canon()` citation tokens, `slot()` book classification, `near()` |
| `audit_readings.py YEAR` | app vs oca.org -> `data/oca_readings_diff-YYYY.json` |
| `explain_diff.py DATE...` | both sides of one day in full, with sources and labels |

Everything is cached under `data/oca_raw/_cache/`, so re-running a harvest is
instant. That matters: at a 10-second crawl delay a fresh year of saints is
about an hour. Delete the cache only if you mean to re-fetch.

`refs.py:canon()` came from `tools/greek/three_way.py`, where the ordinal and
single-chapter traps were worked out. Prefer this copy for new work.

## Typical run

```sh
python tools/oca/harvest_readings.py 2026            # no Django needed
docker compose run --rm local python tools/oca/audit_readings.py 2026
docker compose run --rm local python tools/oca/explain_diff.py --all 2026
```

The harvests are plain HTTP and run on the host; the audits need Django and run
in the container.

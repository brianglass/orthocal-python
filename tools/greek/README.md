# Greek lectionary analysis tooling

Throwaway-but-kept analysis scripts backing `docs/greek-weekday-drift.md`.
**None of this is application code** — nothing in `calendarium/` imports it.
It exists so the claims in that document can be re-derived rather than taken
on trust, and so the next investigation starts from the harvested evidence
instead of re-scraping it.

Run from anywhere; each script re-roots itself at the repo. The ones that
touch the ORM need the Django environment:

    python3 tools/greek/greek_labels.py                       # no Django
    docker compose exec -T local python tools/greek/rule_verify.py

## The evidence, and what proves it

| claim in the doc | script | data |
|---|---|---|
| the Greek-native lectionary reconstructed from antiochian.org's own slot labels | `greek_labels.py` | `data/greek_lectionary_from_labels.json` |
| the ordinary weekday formula holds at `lag = -1`, 303 days / 9 cycles | `greek_labels.py` | `data/antiochian_raw/` |
| the Luke-section cycle is back-anchored to Triodion (289 observations, 0 exceptions) | `backanchor.py` | `data/goarch_pointer_sequences.txt` |
| the app is right on the back-anchored tail and wrong on the surplus weeks | `backanchor_audit.py` | as above |
| the Theophany-interpolation rule (25 cycles, 0 failures) | `rule_verify.py` | `data/goarch_sunday_sequences.txt` |
| GOA's Triodion disagrees with the Paschalion in exactly 2 of 30 cycles | `pp_align.py` | as above |
| the app followed GOA on weekdays but Antiochian on Sundays | `sunday_alleg.py` | both sources |
| GOA vs Antiochian differ on ~4 days in calendar 2026 | `fingerprint.py` then `year_diff.py` | `data/goa2026.txt`, `data/ant2026.txt` |

## Harvesting more

antiochian.org has a JSON API (`ingest_antiochian.py`) but reaches only 2018
through roughly a year ahead. goarch.org has no API and sits behind Cloudflare,
but serves 2011-2060+ — every question closed as "unobservable" on
antiochian's horizon should be reconsidered against it.

To harvest goarch.org: open any goarch.org page in a real browser, clear the
Cloudflare interstitial by hand once, then `fetch()` further months from
inside the page origin — same-origin requests inherit the clearance for the
rest of the session. The month grid parses out of `innerText` as
`[day, long date, fasting lines, label, saints..., 'Epistle Reading', '-',
epistle, 'Gospel Reading', '-', gospel]`.

**Treat goarch.org's generated years as fallible.** Past their published
Kanonion horizon they are pure algorithm, which makes them a clean oracle for
the *reading cycle* — but their pre-Lenten labels carry real errors (see
`pp_align.py`, and 2035, where they print "Publican and Pharisee" on two
consecutive Sundays).

## Surplus-week investigation

| question | script |
|---|---|
| how many days a year fall in the surplus region | `surplus_impact.py` |
| per-cycle map of weeks-before-Triodion -> week read | `surplus_map.py` |
| is the surplus the forward pointer still running? (no: 0/22) | `surplus_forward.py` |
| does the app extend the back-anchor backward? (yes: 302/302) | `surplus_app_rule.py` |

`data/goarch_daily_long_cycles.txt` holds full daily Gospels for three clean
long cycles. To add more, use the `__daily()` harvester described above — one
browser call per cycle returns a whole Jan-Mar window compactly.

## Annual-ordo overlay

| purpose | script |
|---|---|
| how many Jan 19/24/26 slots disagree with the app | `ordo_coverage.py` |
| do the curated values drain a computable pool? (no) | `ordo_pool.py` |
| resolve ordo citations to pdists, and emit the table | `ordo_resolve.py` |

`ordo_resolve.py` prints `_GREEK_ORDO_GOSPEL` ready to paste into
`calendarium/liturgics/year.py`. Re-harvest goarch.org first (see above) when
GOA publishes a new Kanonion; the table is currently good through January 2027.

`load_ordo.py` populates `models.OrdoReading` for both jurisdictions and prints
the two commands needed to regenerate `fixtures/calendarium.json`. Run it after
re-harvesting when a new annual ordo is published.

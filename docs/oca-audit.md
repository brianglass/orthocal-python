# Auditing the Slavic data against oca.org

The Slavic readings have been in this app since long before the Greek tradition
was added, and they were never measured against their own source the way Greek
was measured against goarch.org (`docs/greek-lectionary.md`, which took Greek
from 96.1% to 99.1%). This is that measurement.

**Current state: 329/339 dates match for 2026 — 97.1%.** Ten dates differ, in
three coherent groups, and the largest group is a single unmodelled rule rather
than ten separate mistakes.

## Sources

| what | URL | cost |
|---|---|---|
| a year of Liturgy readings | `/readings/monthly/YYYY/MM` | 12 pages |
| one day, all services | `/readings/daily/YYYY/MM/DD` | 1 page |
| one day's commemorations | `/saints/lives/YYYY/MM/DD` | 1 page |

oca.org's `robots.txt` allows all of these — it disallows only two unrelated
paths — and asks for `Crawl-delay: 10`, which `tools/oca/fetch.py` honours and
caches around.

**It 403s some user agents on a keyword match.** A UA containing the word
"harvester" is refused, as is `python-urllib/3.14`; an honest self-identifying
string is served fine. That is a crude keyword filter, not an access policy —
robots.txt is the policy. Identify yourself properly; do not impersonate a
browser.

## Two traps in the monthly tables

Both of these produced confidently wrong numbers before being caught.

**The columns are not positionally stable.** January and May–December give four
cells a row; February, March and April give five. The extra column is not
consistently anything — on 2/1 it is empty with the Epistle and Gospel after
it, while on 2/18 a Lenten day's two Old Testament lessons sit in the very
cells a Liturgy day uses for Epistle and Gospel. Reading slots off column
numbers swaps Epistle and Gospel for a third of the year: it scored the app at
**73.7%** when the true figure was far higher. Classify by book instead —
`tools/oca/refs.py:slot()`.

**"Slot" is two axes, and the two sources name different ones.** A reading has
a *kind* — Gospel, Epistle, Prophecy — and a *service* it is read at. These are
independent. Holy Week's Bridegroom readings are Gospels **and** are read at
Matins; oca.org's `(Matins)` names the service and the app's `Gospel` names the
kind, and neither is wrong.

The app's `source` is compositional over both axes, with either omissible:

| source | service | kind | rows |
|---|---|---|---|
| `Gospel` | Liturgy, implied | Gospel | 617 |
| `Vespers` | Vespers | Old Testament in practice — see below | 358 |
| `Matins Gospel` | Matins | Gospel | 72 |
| `6th Hour, Epistle` | Sixth Hour | Epistle | 4 |

So a bare `Gospel` means *Liturgy* Gospel by default. Six Holy Week rows are the
exception: the four Bridegroom gospels and the two at the Washing of the Feet
carry `source='Gospel'` and name their service in `desc` instead
(`Bridegroom`, `At the Washing of the Feet`). A reader loses nothing — the desc
is displayed — but a matcher keying on `source` alone reads them as Liturgy
gospels.

This is why excluding oca.org's service-labelled rows to compensate made things
*worse* — 95.6%, with false differences on exactly the hardest days. The two
sources were being asked to agree on an axis neither was consistently naming.

**`Vespers` implies Old Testament, and its exceptions are principled.** Of 359
Vespers rows, 320 (89%) are Old Testament lessons. The exceptions are not
noise:

- **38 are Catholic Epistles on apostolic feasts** — three lessons from James
  for St James, three from 1 Peter for St Peter, three from 1 John for St John,
  three from Jude. On an apostle's feast the three Old Testament lessons are
  replaced by three from the catholic epistles, which is exactly what these
  are. Correct as stored.
- **1 is a genuine Vespers Gospel**, `John 20:19-25`, with its own `source`
  value saying so.

So the useful rule for reading this data is that a bare `Vespers` means an Old
Testament lesson unless the day is an apostle's feast. Useful in both
directions: an unexplained New Testament reading under `Vespers` on a
non-apostolic day would be worth a second look.

One classifier note: 38 Vespers rows are composite lessons whose display names
books and chapters but no verse — `Composite 2 - Proverbs 10, 3, 8`. `canon()`
needs a chapter:verse and returns nothing for them, so `refs.classify()` falls
back to the book name. They can be *classified* but never *matched* by
citation; all 38 are Old Testament, so nothing in this audit turns on them.

So the audit does not pair readings by slot at all. It asks two questions
separately:

- **missing** — oca.org lists it and the app has it nowhere. A real gap.
- **extra** — the app shows it as an Epistle or Gospel and oca.org lists
  nothing like it. Restricted to those two sources so the app's much fuller
  Vespers and Hours data is not counted against it.

## What differs

Every date below was confirmed against `/readings/daily/`, which lists all
services, in case the monthly table was abbreviating. It was not.

### 1. The ordinary daily cycle on feast days — 4 dates, one rule

The app and oca.org disagree about whether the ordinary daily-cycle reading is
*also* read when a feast or its eve claims the day. Both directions occur:

| date | day | oca.org | the app |
|---|---|---|---|
| Jan 1 | Circumcision + St Basil | reads `Heb 10:35-11:7` / `Mark 11:27-33` as well | omits it |
| Jan 5 | Eve of Theophany | reads `Heb 11:17-23,27-31` / `Mark 8:11-21` as well | omits it |
| Dec 24 | Eve of Nativity | reads `Heb 10:35-11:7` / `Mark 10:17-27` as well | omits it |
| Jan 3 | Saturday before Theophany | reads **only** `1 Tim 3:14-4:5` / `Matt 3:1-11` | adds `Eph 5:1-8` / `Luke 17:3-10` |

The first three are one rule and the fourth is its mirror, which is what makes
this worth fixing as a rule rather than four data rows: on a *feast or eve* the
ordinary reading survives alongside the festal one, and on a *Saturday or
Sunday before or after* a great feast it is replaced. The app currently has it
backwards in both cases.

Not yet implemented — the fix belongs in the reading-selection logic, and the
rule above is inferred from four dates in one year. **Confirm it across several
years before coding it**, the same standard the Greek work held to.

### 2. Readings the app shows on days oca.org gives to Holy Week — 3 dates

| date | day | the app also shows |
|---|---|---|
| Apr 7 | Great and Holy Tuesday | `Matt 22:15` (Bridegroom), `John 10:9` (St Tikhon) |
| Apr 9 | Great and Holy Thursday | `John 13:1-11`, `John 13:12-17` (the Washing of the Feet) |
| Oct 31 | — | `Heb 13:7`, `Luke 8:16`, `Luke 12:32`; oca.org has `John 10:9` |

Apr 7 is the informative one. The Repose of St Tikhon falls on Great and Holy
Tuesday in 2026, and oca.org gives him no readings at all — Holy Week
suppresses them. The app serves them. This is a ranking question, not a data
error, and it is the same shape as the fast-exception ranking work in
`docs/greek-fasting.md`.

The two foot-washing gospels on Apr 9 are genuinely served, and the app has
them right — they are Gospels, read at the Washing of the Feet, and `desc` says
so. They surface here only because oca.org's monthly table does not list them
and the audit's "extra" direction keys on `source`, where they look like
Liturgy gospels. Nothing to fix; see the two-axis note above.

### 3. Single dates, not yet explained — 3 dates

`2026-03-26` (missing `Heb 2:11` / `Luke 1:24`), `2026-05-21` (extra
`Acts 26:1` / `John 10:1`), `2026-11-08` (extra `1 Cor 12:27` / `Matt 10:1`).
All three are feast-adjacent — the Synaxis of Gabriel, Constantine and Helen,
and the Synaxis of the Archangel Michael. They may well fall under group 1 once
that rule is confirmed across more years.

## What this does not cover

The monthly tables give the Liturgy, plus Vespers Old Testament lessons in the
Lenten months only. **Matins is not covered at all, and Vespers only partly**,
so a clean report here says nothing about them. The app's Vespers and Hours
data is far fuller than anything checked here.

`/readings/daily/` *does* list every service — Jan 1 returns all ten readings
including the Vespers and Matins ones — and would support a complete audit at
365 requests a year rather than 12. That is the obvious next step if the
Liturgy-level gaps above turn out to be worth chasing.

Only 2026 has been audited. One year is enough to find a rule but not to
confirm one.

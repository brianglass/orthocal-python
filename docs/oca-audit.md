# Auditing the Slavic data against oca.org

The Slavic readings have been in this app since long before the Greek tradition
was added, and they were never measured against their own source the way Greek
was measured against goarch.org (`docs/greek-lectionary.md`, which took Greek
from 96.1% to 99.1%). This is that measurement.

**Current state, five years harvested (2023-2027): 97.0% to 98.2% a year.**
Nearly every remaining difference is one unmodelled rule rather than a
collection of separate mistakes. See "Five years changes the diagnosis" below;
**one year was actively misleading** about which dates matter.

| year | dates | match | differ |
|---|---|---|---|
| 2023 | 338 | 330 | 8 |
| 2024 | 338 | 328 | 10 |
| 2025 | 337 | 331 | 6 |
| 2026 | 339 | 329 | 10 |
| 2027 | 338 | 328 | 10 |

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

# Composite readings: recovering the verse selections

The `Composite` table holds 24 hand-entered readings in Archimandrite Ephrem
Lash's translation (`~/src/anastasis`). Each is stitched from verses that no
plain reference names, and until now most carried only a chapter-level
`sdisplay` — `Prov 10, 3, 8`, `Isa 40, 41, 45, 48, 54`. Those are inert,
because a composite pericope resolves through the table rather than through
`sdisplay`, but they are wrong if resolved: `Isa 40, 41, 45, 48, 54` fetches
123 verses where the reading is ten.

**Nobody publishes the selection.** Ephrem writes "and selection"; oca.org
titles a composite by chapter and numbers its *parts* (1, 2, 3) where an
ordinary reading gets true verse numbers; orthodox_calendar stores opaque
`NNNMM` part keys. The text is the only record of what a composite contains.

## Method

oca.org publishes the same composite corpus under the same numbering —
verified word-for-word identical to orthodox_calendar on Composites 17 and 18,
181 and 209 words with zero differences. It is *not* Ephrem's translation, so
it is useless as replacement text, but it is excellent evidence of **which
verses** a composite covers.

So each composite was read against our Bible by eye, part by part, and the
selection written down. Deliberately not by similarity threshold: the numbers
below are a check on a reading already done, not the thing that made the
decision. Composite 18's error was found by reading, and no threshold would
have flagged it.

Fidelity is measured as word-level similarity between oca.org's text and our
LXX2012-WEB rendering of the derived reference. **The sixteen specs that were
already precise score 59–78%**, so that band is what a correct selection looks
like; the gap from 100% is translation, not selection.

## Results

| composite | was | now | fidelity | |
|---|---|---|---|---|
| 13 — 3 Kgs 18, 19 | 62% | `18:1, 17-46; 19:1-16` | **74%** | in band |
| 8 — Isaiah | 11% | `40:1-3, 9; 41:17-18; 45:8; 48:20-21; 54:1` | **66%** | in band |
| 2 — Proverbs | 17% | `10:7, 6; 3:13-16; 8:32, 34-35, 4, 12, 14, 17, 5-9` | **64%** | in band |
| 3 — Wisdom | 24% | `4:7, 16-17, 19-20; 5:1-7` | 56% | marginal |
| 9 — Malachi | 34% | `3:1-3, 5-7, 12, 17-18; 4:6, 4-5` | 54% | marginal |
| 6 — Exodus/Lev/Num | 15% | `Exod 13:1-3, 11-12, 14-16; Lev 12:2-4, 6-8; Num 8:16-17` | 53% | marginal |
| 4 — Prov/Wisdom | 15% | `Prov 10:31-32; Wis 6:12-16; 7:30; 8:2-4, 7-8; 9:1-5, 10-11, 14` | 44% | not stored |
| 5 — Wisdom | 17% | `4:1, 14; 6:12, 17-18, 21-22; 7:15, 22, 26-27, 29-30; 2:1, 10-20` | 37% | not stored |

**None of the derived specs are stored.** They are recorded above as research,
and the decision (2026-08-28) was to keep the composite mechanism as it is:
Ephrem's text for the 22 that have it, and the zero-width-space fall-through
for 17 and 18.

That decision follows from the table. Only three of eight derivations reach the
band a correct selection occupies, and the other five sit below it -- so there
is no clean path to references, and a partial conversion would render some
composites in the reader's translation and others in Ephrem's, on the same
page, for no gain in what the reader sees.Storing them was tried and reverted for a reason worth keeping in mind:
`sdisplay` is not a private note. `calendarium/api.py` publishes it as the
API's `short_display`, documented as "the scripture reference with abbreviated
book name". For a composite there is no such reference, and the loose form is
what oca.org itself prints as the title -- so an enumerated 54-character guess
would both break with convention and assert a precision measured at 53-64%.
Composite 5's derived spec was also 67 characters against the column's
`max_length=64`.

(Three *pre-existing* sdisplay values already exceed that limit -- the Holy Week
composite gospels at pks 116, 120 and 1013, 72-73 characters each. SQLite does
not enforce max_length so they work, but they would fail validation or another
backend.)

**Composites 4 and 5 should not be converted to references.** Their low scores
are not a failure to find the right verses — adding candidate verses made them
*worse*, 44%→43%→40% and 37%→37%→35%. They are free adaptations rather than
selections, condensing and reordering within verses, so no reference can
represent them. Composite 2's part [2] shows the pattern at its most extreme
even where the verses are findable: 8:32, then 34-35, then 4, 12, 14, 17.

Two notes on the ordering, both already handled: `bible.models.lookup_reference`
renders out-of-order segments in the order written (see `calendarium/models.py`),
and Composite 9's third part really does run 4:6 before 4:4-5.

## Where this leaves the composites

Unchanged, deliberately. Ephrem's text stays, and 17 and 18 keep falling
through to a scripture reference. Two corrections did land, because neither is
inference:

- **Composite 18** was `3 Kgs 7:51-8:1, 8:4-7, 9-11`, which included a verse
  oca.org's text does not have and omitted one it does. Now
  `3 Kgs 8:1, 3-7, 9-11`. This one is *functional* -- it is a fall-through, so
  the range is what readers actually get.
- **Composite 24** was `Lev 26`, the whole 46-verse chapter, where the reading
  is 21 verses. Ephrem spells this one out in full, so the spec is his rather
  than derived.

The remaining six loose `sdisplay` values are left as they are. They are
inert -- those pericopes resolve through the Composite table -- and the trap
they would pose if resolved is recorded in `calendarium/models.py`.

Composites 17 and 18 remain the two with no Ephrem text at all: they are the
Slavic propers for the Entrance of the Theotokos, absent from his
Prophetologion, which assigns the Greek Marian set to that feast instead.


# Five years changes the diagnosis (2026-08-28)

The sections above were written from 2026 alone. Harvesting 2023-2027 and
cross-tabulating by month-day corrected two conclusions:

| date | years differing | |
|---|---|---|
| **10-31** | **5 of 5** | filed above as a one-off single date |
| 01-05 Eve of Theophany | 4 of 5 | |
| 12-24 Eve of Nativity | 4 of 5 | |
| 01-01 Circumcision | 3 of 5 | |
| 01-02, 01-03, 01-04 | 1 each | not three dates -- the Saturday before Theophany moving |

Jan 3 is not a fixed-date problem; it is whichever day the Saturday before
Theophany lands on. And Oct 31 is not a one-off; it is the single most
consistent difference in the whole audit. **One year of data is enough to find
a candidate and not enough to rank it.**

## Fixed: St John Kochurov, Oct 31

oca.org gives him a proper Gospel and no proper Epistle. The Epistle differs
every year -- Col 2:20-3:3, Phil 1:20-27, Col 2:1-7, 2 Cor 5:1-10,
2 Cor 11:31-12:9 -- which is what proves it is the ordinary daily reading; the
Gospel is `John 10:9-16` in all five.

The app had `Heb 13:7-16` and `Luke 12:32-40`, both plausible hieromartyr
commons. Gospel repointed, Epistle row removed. Oct 31 now differs by one
citation a year instead of three.

(When checking locally, note that `loaddata` is additive: it will not remove a
deleted row from an existing dev database, and the audit kept reporting the
removed Epistle until it was deleted explicitly. Production rebuilds from the
fixture at image build, so it is unaffected.)

## The remaining rule, and why it is not implemented

Everything still differing is one question: **does the ordinary daily reading
coexist with a proper one?** It runs both ways.

- The app *drops* the daily reading where oca.org keeps it -- Jan 1, Jan 5,
  Dec 24.
- The app *keeps* it where oca.org replaces it -- Oct 31, and the moving
  Saturday before Theophany.

Implementing it would close roughly 4-5 of the 6-10 differing dates a year,
call it 97% to 98.5%. **Paused deliberately (2026-08-28), because the harness
cannot yet prove such a change safe.**

### What the harness does and does not cover

| harness | scope | baseline |
|---|---|---|
| this audit | 5 years x ~338 days = 1,690 comparisons vs oca.org | 97.0-98.2% |
| `tools/greek/goa_gap.py` | 336 days vs goarch.org | 333/336, 99.1% |
| unit tests | | 189 |

**The reading-selection logic is shared.** `aget_readings` is on the base `Day`
class (`calendarium/liturgics/day.py`), which both `SlavicDay` and `GreekDay`
inherit, so a change made for Slavic accuracy is measured for Greek against a
*different* source. A Slavic improvement can cost Greek silently.

**Both audits check the Liturgy Epistle and Gospel only -- 894 of 1,446
readings a year, so 38% is unmeasured.** The blind spot is exactly where this
rule operates: Jan 1, Jan 5 and Dec 24 are the days heaviest with Vespers,
Matins and Hours, and Theophany Eve alone renders thirteen Vespers lessons and
four sets of Hours. Jan 5's Liturgy readings could be brought into agreement
while its Royal Hours were wrecked, and every harness would stay green.

Smaller gaps: 26-28 Lenten days a year are skipped as Old-Testament-only; five
years does not cover rare weekday configurations of these feasts; the Greek
audit is one year, because goarch.org is harvest-limited.

### Prerequisite before touching the logic

1. **Extend the audit to `/readings/daily/`**, which lists every service --
   the same pages used to verify Jan 1 and Dec 24 above. That closes the 38%.
   365 requests a year at the 10-second crawl delay, about an hour, cached
   permanently. This is a prerequisite, not an optional extra.
2. Run both audits before and after. A Greek regression is a stop, not a
   trade.
3. Pin tests on the dates the rule must change *and* neighbours it must not.
4. Scope the rule to what the evidence covers rather than to a general
   principle about propers and daily readings.


# The all-services audit (2026-08-28)

The prerequisite named above is done. `tools/oca/harvest_daily.py` pulls
`/readings/daily/YYYY/MM/DD`, which lists **every** service, and
`tools/oca/audit_daily.py` compares the whole day on both sides. Theophany Eve
returns 34 readings there against the monthly lectionary's two.

**Baseline for 2026: 352/365 dates match exactly (96.4%)**, comparing 1,448 app
readings against 1,438 from oca.org. The older Liturgy-only figure of 97.1% was
measuring 62% of the data.

The good news is where the differences are *not*. The 38% that was previously
unmeasured is almost entirely clean: Theophany Eve's thirteen Vespers lessons,
four sets of Hours and Blessing of Waters all match exactly, and the day
differs only in the two Liturgy readings already known about.

## It immediately caught a bad fix of ours

The Oct 31 change committed earlier that same day deleted St John Kochurov's
`Hebrews 13:7-16` and repointed his `Luke 12:32-40`, because the monthly
lectionary showed neither, in five consecutive years. The daily page lists both,
labelled by oca.org itself as *(Epistle, St. John Kochurov)* and *(Gospel, St.
John Kochurov)*. The app had been right except for omitting `John 10:9-16`.

So: **the monthly lectionary is lossy, not merely Liturgy-only.** It keeps one
reading set per label and drops others, including ones oca.org labels Epistle
and Gospel. No rule about which services it covers would have predicted this.
Use `/readings/daily/` for anything that will change data.

This is exactly the failure the coverage note above predicted in the abstract,
arriving before the logic change it was written about, and against a change
that had five years of consistent evidence behind it.

## What differs now

| date | | |
|---|---|---|
| 05-21 | extra 6 | Constantine and Helen -- Vespers lessons oca.org does not list |
| 11-08 | extra 5 | Synaxis of the Archangel Michael, same shape |
| 11-14 | extra 4 | Apostle Philip -- the catholic-epistle Vespers set for an apostle |
| 03-30 / 03-31 | 3 each way | **a one-day offset**: Composites 2, 3 and 4 sit on Mar 30 here and Mar 31 on oca.org |
| 06-30 | missing 3 | Synaxis of the Twelve Apostles -- `Isa 43:9`, `Wis 3:1`, `Wis 5:15` |
| 07-05 | extra 3 | Athanasius of Athos |
| 01-01, 01-05, 12-24 | missing 2 | the feast-eve rule, unchanged |
| 01-03 | extra 2 | its mirror, the Saturday before Theophany |
| 03-26, 04-07 | | as before |

The Mar 30/31 pair is a new kind of finding the Liturgy-only audit could not
see: not a wrong reading but a wrong *date*, and the two entries cancel out in
any per-year total. `Isa 43:9 / Wis 3:1 / Wis 5:15` appearing as missing on
Jun 30 and extra on Nov 8 may be the same shape.

# Choosing the abbreviated readings

`Day.aget_abbreviated_readings()` reduces a day to one Epistle and one Gospel;
it is what the Alexa skill speaks. It was hand-tuned and had never been
measured, because there was no obvious ground truth for "the" reading of a day.

There are three, and they disagree usefully:

- **antiochian.org and goarch.org publish exactly one pair a day.** That is a
  direct answer, and on every feast checked the two agree with each other.
- **oca.org's monthly lectionary lists reading sets per date**, propers
  labelled and the ordinary set unlabelled. Useful, but **its row order is not
  reliably primary-first** -- Jan 1 leads with Circumcision, while Feb 2, the
  Meeting of the Lord, leads with the *daily* reading and puts the feast
  second. Do not treat the first row as the answer.

## The rule, measured

Against antiochian.org for 2026, on days that have a proper:

| feast level | proper wins | daily wins |
|---|---|---|
| 0 | 18 | 22 |
| 2 | 20 | 16 |
| 3-5 | 47 | 14 |
| 6-7 | 8 | 0 |
| 8 | 5 | 1 |

So the proper takes over somewhere around level 3, and below that the ordinary
daily reading is more often right -- which matches the intuition that a minor
commemoration does not displace the daily cycle.

Splitting levels 3 and up by weekday sharpens it considerably:

| | proper | daily |
|---|---|---|
| **Sunday** | 1 | 7 |
| **weekday** | 59 | 8 |

**Sunday is why this logic cannot live in the data.** On a Sunday the
resurrectional reading takes precedence over almost any saint, and whether a
fixed date falls on a Sunday changes from year to year, while `ordering` is a
static column. Retiering rows alone would get Sundays wrong.

**Floating commemorations rank ahead of all of it**, Sunday included. They are
not a saint landing on a day, they *are* the day -- the memorial Saturdays, the
Sundays of the Forefathers and of the Fathers, the Saturdays and Sundays before
and after a great feast. oca.org prints their readings first (Demetrius
Saturday leads with the Departed pair, the Saturday before Nativity with its
own), and the Sunday statistic above was measured on saints *displacing* a
Sunday, which is a different question. A float is identified by a `pdist` at or
above 1000, the base of `FloatIndex`.

The implemented rule is therefore: floats first; then, when
`feast_level >= 3` and the day is not a Sunday, the day's propers; otherwise
the ordinary daily readings; falling back to whatever exists.

The Lenten soul Saturdays needed a data change rather than a rule. Their
Departed readings are not floats -- they carry the day's own `pdist` and were
distinguished only by `desc` and an `ordering` of 812/912, one tier *below* the
daily cycle. Since those days are always Saturdays, static ordering can express
the precedence, so the twelve rows moved to 802/902. Demetrius Saturday needed
nothing; its Departed readings are already a float at `pdist=1003`. Lenten weekdays are untouched --
there is no Epistle/Gospel pair to reduce to, so the Old Testament readings
(Sixth Hour Isaiah, Vespers Genesis and Proverbs) pass through for every
tradition, which is correct.

Measured against oca.org's leading pair, this moved 2026 from **244/339
(72.0%) to 294/339 (86.7%)** -- 83.5% from the rank rule, 85.0% once floats
rank first, 86.7% with the soul Saturdays retiered. That understates it, since the metric counts Feb 2
as a miss where we now agree with antiochian.org and goarch.org.

A cleaner metric for the Greek tradition -- its abbreviated pair against
antiochian.org -- is not yet usable: it conflates the selection logic with
known gaps in the Greek proper data and with Lenten days where antiochian's two
readings are Old Testament rather than Epistle and Gospel. Separating those is
worth doing before trusting a number from it.

## The Annunciation on a Lenten weekday

It shows its own Epistle and Gospel, `Hebrews 2:11-18` / `Luke 1:24-38`,
confirmed on the 2024, 2026 and 2027 occurrences -- Monday, Wednesday and
Thursday of Lent respectively. A plain Lenten weekday still yields only the Old
Testament set, for both traditions.

Worth knowing *why* it works, because it is not obvious: Mar 25 has **no
fixed-date Epistle or Gospel rows at all**. Its readings are floats, which is
what makes them survive both the Lenten suppression and the rank rule. A tier
audit looking only at `month`/`day` rows reports "no Epistle/Gospel rows" for
the Annunciation and that is not a fault.

# The rank exception on ordinary Wednesdays and Fridays (2026-09-01)

Brian was notified that St Tikhon's calendar lightens Jul 24 to wine and oil,
where this app had a full abstention. Investigating it found a systematic gap,
though **not** one that explains the reading differences above -- of the 13
affected dates, only Jun 30 also appears in either readings audit. It is its own
axis.

`_apply_fasting_adjustments` had cases for Lent, Dormition and the
Apostles'/Nativity fasts, and **none for the ordinary Wednesday and Friday
fast**. Outside the four great fasts, `fast_exception` came entirely from the
data with no rank adjustment -- and the data is not consistent, because at
feast level 4 the fixture carries 0 for Boris and Gleb and Constantine and
Helen, 1 for Job of Pochaev, and 2 for Sergius of Radonezh.

**It cannot be consistent, because it is in the wrong place.** `fast_exception`
is baked onto a fixed-date `Day` row, but whether that date lands on a
Wednesday or Friday changes from year to year. This is the same structural
point as the Sunday rule for abbreviated readings: a weekday-conditional rule
cannot live in a static per-date column.

## Sources

antiochian.org is no use here. It reports Jul 24 2026 as a full abstention, but
its title for the day is "8TH FRIDAY AFTER PENTECOST" -- Boris and Gleb are not
in the Antiochian calendar at all, so no rank exception could apply. oca.org
publishes no fasting information on either its readings or its lives pages.

`holytrinityorthodox.com/calendar/calendar.php?month=M&today=D&year=Y` does,
one dietary line per day. **But its robots.txt disallows `/calendar`**, which
was not checked until after the queries below had been made -- an error, and
the reason that sample was not widened. Do not scrape it. Its `Crawl-delay` is
120 seconds for the paths that are allowed. Note it reckons **old calendar**: a fixed date N
appears there on Gregorian N+13, so the weekday differs from this app's, and a
commemoration has to be looked up in a year where *its* day falls on a
Wednesday or Friday.

Checked that way, on days where the commemoration falls on a Wednesday or
Friday:

| commemoration | our level | holytrinityorthodox.com | this app, before |
|---|---|---|---|
| Boris and Gleb | 4 | Fast. Food with Oil | strict |
| Anthony of the Kiev Caves | 4 | Fast. Food with Oil | strict |
| Synaxis of the Twelve Apostles | 4 | Fast. Food with Oil | strict |
| Sep 11 | 4 | Fast. Food with Oil | strict |
| Leavetaking of Theophany | 4 | Fast. **Fish** Allowed | strict |
| Greatmartyr Marina | 4 | Fast. Food with Oil | strict |
| Adrian and Natalia | 4 | Fast. Food with Oil | strict |
| **St Sava of Serbia** | **3** | Fast. **Fish** Allowed | strict |

**Seven of seven at level 4 confirm the rule**, in the direction it was
applied, and none contradicts it.

Two further samples were discarded as invalid, and the mistake is worth
recording: the date arithmetic found a year where each commemoration lands on a
Wednesday or Friday, but did not check that the day is an *ordinary* fast in
holytrinityorthodox.com's own reckoning. Greatmartyr Theodore Tyro fell inside
Great Lent (plain "Fast") and Constantine and Helen inside a fast-free week
("Fast-free Week"). Neither says anything about the ordinary Wednesday and
Friday rule. Filter on the season, not just the weekday.

**The control did not behave as expected, and that is the interesting result.**
St Sava is level 3 here, below the threshold the rule uses, and
holytrinityorthodox.com relaxes his day all the way to fish. So this app may
still be too strict on level-3 days.

That is not necessarily a threshold error. Our `feast_level` is this project's
own number, and St Sava may simply be polyeleos in ROCOR reckoning where he is
doxology here -- the same confound that made the Greek measurement unusable.
What it does establish is that the error the rule leaves behind is one of being
*too strict*, never too lenient, which is the safe direction to be wrong in.

### Chasing the threshold: inconclusive, and why

Four more samples were taken at levels 3 and 2, this time filtering on the
season. All four came back "Fast. Fish Allowed", which looks at first like
strong evidence that the threshold should be far below 4. It is not.

A control settles it: **2026-04-29, a plain Wednesday in the Paschal season
with only two minor virgin-martyrs commemorated, also gives "Fast. Fish
Allowed."** So the Paschal season relaxes Wednesday and Friday to fish
irrespective of rank, and the two April samples were measuring the season. A
second control confirmed the other end -- 2026-02-04 returns "Fast-free Week",
the week of the Publican and Pharisee.

That leaves two samples, neither clean: the Synaxis of the Forerunner sits in
the relaxed days after Theophany and is a significant feast in its own right,
and Paul of Thebes at level 2 is unexplained but falls days before the Triodion.

**The threshold below level 4 is therefore still unknown.** Testing it needs
samples drawn from ordinary time -- outside the Paschal season, the Triodion,
the four fasts and the fast-free weeks -- and the season filter used here was
not strict enough to guarantee that. The rule as shipped rests on seven
level-4 confirmations and is unaffected.

### OCA publishes the rules, which settles several of these

<https://www.oca.org/liturgics/outlines/fasting-fast-free-seasons-of-the-church>
states the rules rather than showing sampled days, which is what was wanted.
Brian pointed to it (2026-09-02). Everything it states outright, this app
already gets right: Trinity Week and the week of the Publican and Pharisee are
fast-free, Cheesefare is a Meat Fast, and the Eve of Theophany, the Beheading
and the Elevation are fast days.

**It also deflates the Paschal-season candidate below.** The page lists Bright
Week and Trinity Week as fast-free and otherwise says "the Wednesdays and
Fridays of the Year" are fast days, with no fish allowance for the Paschal
season at all. This app already gives wine and oil there, which is *more*
lenient than OCA's stated rule, so holytrinityorthodox.com's fish is ROCOR
practice rather than a gap here. Candidate withdrawn.

**It states the Lenten named list**, which turned out to be three-quarters
implemented. Wine and oil are permitted on nine named dates "if they fall on a
weekday in the second, third, fourth, fifth or sixth week". Checking each in
years where it does:

| | granted |
|---|---|
| Feb 27, Mar 24, Mar 26, Mar 31, Apr 7, Apr 23 | 3 of 3 each |
| **Feb 24**, 1st and 2nd Finding of the Head | **0 of 1** |
| **Mar 9**, Forty Martyrs of Sebaste | **0 of 3** |
| **Apr 25**, Apostle Mark | **0 of 2** |

The three are now set to `fast_exception = 1` (2026-09-02). They are left
`common` rather than split: antiochian.org grants wine and oil on Mar 9 in both
2020 and 2026 and on Apr 25 in 2024, confirming those are shared and not
Slavic-only. Feb 24 has no qualifying harvested year, so its Greek side is
assumed rather than verified.

No scoping logic was needed. Week 1 and Holy Week already exclude themselves,
because those pdist rows carry `fast_exception = 10`, "No overrides", and
`Day.fast_exception` takes the max -- which is why Feb 24 correctly stays strict
in 2026, when it falls in the first week.

### A caution about the rank rule this document does *not* state

The Typikon quotation on that page is scoped to the Apostles' and Nativity
fasts, not to ordinary Wednesdays and Fridays:

> "If there occur on Tuesday or Thursday a Saint who has a [Great] Doxology, we
> eat fish; if on Monday, the same; but if on Wednesday or Friday, we allow only
> oil and wine…. If it be a Saint who has a Vigil on Wednesday or Friday … we
> allow oil and wine and fish."

Two things follow. First, for the ordinary Wednesday and Friday fast the page
says the opposite of the rule added here: a Fast Day means "no meat, eggs, dairy
products, fish, wine or oil", and rank relaxations are described as "many local
variations … when the feast of a great Saint (or Saints) is celebrated which has
particular local or national significance". **So the rank rule matches OCA's
published *calendar* -- St Tikhon's, and seven of seven on
holytrinityorthodox.com -- but not their published *guidelines*.** It is
defensible as calendar practice; it should not be described as the stated rule.

Second, within the Apostles' and Nativity fasts the Typikon gives thresholds
this app does not implement: doxology rank (level 3) takes wine and oil on a
Wednesday or Friday, and vigil rank (level 5) takes fish. The code's
Apostles'/Nativity branch only ever *reduces* an exception
(`if feast_level < 4 and fast_exception > 1`), never grants one. Worth checking;
not done.

### A separate candidate: Paschal-season Wednesdays and Fridays

The control turned up something larger than the question it was answering.
holytrinityorthodox.com allows **fish** on Paschal-season Wednesdays and
Fridays; this app allows only wine and oil on most of them:

| 2026 | this app | holytrinityorthodox.com |
|---|---|---|
| Apr 22 Wed | Wine and Oil | Fish Allowed |
| Apr 24 Fri | Wine and Oil | Fish Allowed |
| Apr 29 Wed | Wine and Oil | Fish Allowed |

The app does give fish on a few days in that stretch -- May 6 and May 20 in
2026 -- but from per-date data rather than a rule, so the pattern is uneven.
If fish is right for the whole season from Thomas Sunday to Pentecost, that is
roughly 12 to 14 days a year, appreciably more than the 13 the rank rule
touched.

**Not investigated further and not changed.** One source is not enough for a
change of that size, particularly on a day-count that large, and it should be
established from a source that states the rule rather than from sampled days.

## Confirming it further

Five confirmations stand: Brian's own St Tikhon's calendar for Jul 24, and the
four holytrinityorthodox.com lookups above. Widening that sample is blocked --
its robots.txt disallows the calendar path, azbyka.ru sits behind a DDoS-Guard
JS challenge, and oca.org publishes no fasting at all.

Two routes remain. `days.pravoslavie.ru` and `orthochristian.com` serve no
robots.txt, so nothing is disallowed there, but both are Moscow Patriarchate
rather than OCA. Better, the printed St Tikhon's calendar can settle it
directly: in 2026 the rule changes exactly eight days, all checkable by eye --
Jan 9, Jan 14, Jul 3, Jul 10, Jul 17, Jul 24, Aug 26 and Sep 11, each of which
now reads wine and oil where it previously read a full abstention.

Seven more 2026 days are worth checking as controls, because they carried an
exception from the data before this rule and are untouched by it: Jan 30,
May 8, Jul 15, Aug 28, Sep 25, Oct 9 and Nov 13. If the calendar shows a full
abstention on any of those, the *data* was wrong rather than the rule.

## The rule

Added to `SlavicDay._apply_fasting_adjustments`: at `FastLevels.Fast`, a
commemoration of feast level 4 or higher on a Wednesday or Friday takes wine
and oil. A floor of wine and oil is deliberately conservative -- the Leavetaking
of Theophany case shows the source is sometimes more lenient still.

13 dates a year change from a full abstention to wine and oil; all 45
level-4-and-above ordinary Wednesday and Friday fast days across 2025-2027 now
carry an exception, and days below level 4 are untouched (35 with an exception,
107 strict, unchanged).

**GreekDay is not changed, and that is now a measured decision rather than
caution** -- see "Does the rank exception apply in Greek practice?" below.

## Does the rank exception apply in Greek practice? Not on this evidence.

Tested against antiochian.org's `fastDesignation`, its own official dietary
line, over every ordinary Wednesday and Friday fast day in the harvest
(2018-2026).

Bucketing by *our* `feast_level` is confounded and should not be trusted: that
number is compiled from Slavic sources, so Jul 24 is level 0 for Greek because
Boris and Gleb are not kept at all. It gives 43% strict against 43% wine and
oil at level 4 and above -- a coin flip.

The feed carries no rank field, but `feastDayTitle` is a serviceable proxy: it
shows a plain lectionary slot ("8TH FRIDAY AFTER PENTECOST") unless a
commemoration claims the day. On that split:

| antiochian.org's own title | strict | wine and oil |
|---|---|---|
| a commemoration is named (n=141) | **52%** | 33% |
| a plain cycle label (n=92) | 87% | 2% |

So being commemorated raises the chance of wine and oil sharply, 33% against
2% -- there is clearly *a* rank effect. But **a majority of named days are
still strict**, which is nothing like the Slavic picture, where every sampled
polyeleos day gave wine and oil or better. Named-yet-strict includes the
Apostle Philip, Athanasius of Mount Athos, the Apostle Thaddaeus and James son
of Alphaeus, while Gregory the Theologian, the Three Hierarchs and Theodore the
Commander are relaxed.

Whatever threshold Greek practice uses is therefore higher, or differently
drawn, than the Slavic one -- and neither the feed nor this app's `feast_level`
can identify which commemorations clear it. Applying the Slavic rule to
`GreekDay` would be wrong in the lenient direction on roughly half the days it
touched. **Left alone.** Reopening this needs a Greek source that publishes
rank, not just a dietary line.

## Did orthodox_calendar already handle it? No.

Checked at Brian's request, to rule out a missed conversion.

`lib/core.lib.php`'s `calculateFasting($fast, $level, $feast_level, $dow, $pday,
$year)` has cases for fast-free, Lent, Dormition and the Apostles'/Nativity
fasts, in the same order and with the same thresholds this app uses. **It has no
case for `$fast == 1`, the ordinary Wednesday and Friday fast** -- exactly the
gap found here. And its Jul 24 row carries `daFexc = 0`, identical to ours. The
conversion was faithful; the rule was never there to convert.

Comparing all 366 fixed dates confirms how faithful, and turns up the handful
that do differ:

**`fast_exception`, 7 dates.** We are more lenient on four -- May 7 (Alexis
Toth), May 11 (Cyril and Methodius), Jul 26 (Jacob Netsvetov) and Oct 1
(Pokrov) are Fast Free here against Paul's fish/wine/oil -- and grant wine and
oil on three where he has none: Aug 16, Aug 28 (Job of Pochaev) and Sep 13.

**`feast_level`, 6 dates.** Two of them matter, because the rules written in
this document key on that number: **Jun 30, the Synaxis of the Twelve Apostles,
is level 4 here and 3 for Paul**, and **Nov 16, the Apostle Matthew, is level 6
here and 5 for Paul** -- which is what put it among the "great feast" dates
retiered earlier.

**Do not port Paul's values into the fixtures.** This data has seen a lot of
revision since he stopped work, so where the two disagree the assumption should
be that ours is the later judgement, not that his is the original truth.
orthodox_calendar is a *reference* -- good for answering "was this ever
handled?", as here, and for corroborating a reading or a date. That is the
standing decision (Brian, 2026-09-02).

## One schema difference worth knowing

Paul has **two** level columns where this app has one: `daFlevel`, the level of
the feast, and `daSlevel`, the level of the saint. Our `feast_level` is the max
of the two, on 360 of 366 dates.

That is not a neutral collapse, because Paul's own code uses them differently.
`calculateFasting` and the reading logic are passed `daFlevel` alone;
`daSlevel` is used only to decide the katavasia, which this app does not
implement. So a date like Jan 14, the Leavetaking of Theophany, is `F=0 S=4` for
Paul and level 4 here -- and Paul's fasting logic would treat it as level 0.

In this instance the collapse made the data *better*: holytrinityorthodox.com
gives Jan 14 "Fast. Fish Allowed" when it falls on a Wednesday or Friday, which
a level-0 reading could never produce. But it means feast-level-gated rules here
fire on days the original would not have, and that is worth knowing before
adding more of them.

`daSnote` was kept, as `Day.service_note`. Of Paul's 25 notes, 20 are present
here with identical text.

Five are not, and four of those look like an oversight rather than a revision,
because this app clearly wants such notes -- it generates "Beginning of
Apostles' Fast" in code:

| | Paul's note |
|---|---|
| pdist -70 | Beginning of the Lenten Triodion |
| pdist 0 | Beginning of the Pentecostarion |
| Nov 15 | Begin Nativity Fast |
| Aug 1 | Begin Dormition Fast |

On a closer look one of the four was not lost but *relocated*: pdist -70 keeps
"Beginning of the Lenten Triodion" in `feast_name`, where Paul has it as a note
and leaves `daFname` empty. It is displayed either way.

The other three were genuinely absent and are now added (2026-09-02), since
this is an oversight rather than a revision -- the app already generates
"Beginning of Apostles' Fast" in both `SlavicDay` and `GreekDay`, so it plainly
intends to announce these:

| | note added |
|---|---|
| pdist 0, Pascha | Beginning of the Pentecostarion |
| Aug 1 | Beginning of Dormition Fast |
| Nov 15 | Beginning of Nativity Fast |

The two fast beginnings are worded to match the generated Apostles' Fast note
rather than Paul's terser "Begin Nativity Fast". All three are `common`, so both
traditions get them. The fifth of Paul's notes, a Presanctified note at
pdist -17, is generated dynamically by both codebases and was never a gap.

## Follow-up: is Oct 31's Kochurov data there for ROCOR?

Brian raised this (2026-08-29). The Oct 31 readings for St John Kochurov were
first judged wrong against oca.org's monthly lectionary, then restored when the
all-services harvest showed oca.org has them after all. But there is a further
question underneath: Kochurov is a New Martyr of the Russian Church, and the
data may have been shaped for **ROCOR** practice rather than OCA.

**Not yet checked.** <https://www.holytrinityorthodox.com/htc/orthodox-calendar/>
(Holy Trinity, Jordanville) is the ROCOR calendar to compare against. Worth
doing before any further change to that date -- and worth remembering that
`tradition` here has only `slavic`, `greek` and `common`, with no OCA/ROCOR
axis, so a genuine OCA-vs-ROCOR divergence has nowhere to live in the current
schema.

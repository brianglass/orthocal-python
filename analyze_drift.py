"""Reusable weekday-drift offset tracer.

For a given Greek liturgical year (keyed the same way GreekYear(year) is --
year of Nativity, not of Theophany), walks every cached antiochian_raw date
in the Nov 1 - Feb 10 winter window, extracts the Gospel citation, resolves
it against this project's own common/slavic Reading table by raw pdist, and
prints calendar date / calendar pdist / matched raw pdist / offset.

offset = matched_raw_pdist - calendar_pdist(this year's Pascha)

Only tradition in ('common', 'slavic') rows are matched against, to avoid
circularity against any greek-tagged overlay rows already added this
session.

Usage: ./ve/bin/python manage.py shell -c "exec(open('analyze_drift.py').read())"
   or: DJANGO_SETTINGS_MODULE=... ./ve/bin/python analyze_drift.py <year>
"""

import glob
import json
import os
import re
import sys
from datetime import date, timedelta
from functools import lru_cache

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()

from django.db import connection

from calendarium.liturgics.year import GreekYear
from ingest_antiochian import parse_reading_citation

CACHE_DIR = 'data/antiochian_raw'

_VERSES_RE = re.compile(r'^(.+)_(\d+)_(\d+)$')


@lru_cache(maxsize=1)
def _all_gospel_pericopes():
    with connection.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT r.pdist, p.book, p.verses
            FROM calendarium_reading r
            JOIN calendarium_pericope p ON p.id = r.pericope_id
            WHERE r.source = 'Gospel'
              AND r.tradition IN ('common', 'slavic')
              AND r.pdist IS NOT NULL
        """)
        return cur.fetchall()


def content_at_pdist(citation):
    """Given a normalized 'Book C:V-V' citation, find raw pdist(s) in the
    common/slavic Reading table whose Gospel content matches. Returns a
    sorted list of matching pdist ints.

    Tries an exact sdisplay match first; falls back to a fuzzy match on
    (book, start-verse-code) within a small tolerance, since antiochian.org
    and this project's data occasionally differ by one verse at a citation
    boundary (a handful of confirmed cases from earlier validation work,
    e.g. Mark 10:23-32 vs 10:24-32) -- an exact-only match would wrongly
    report those days as NO-MATCH instead of tracing the drift through them.
    """

    # Pericope.sdisplay uses 'Book C.V-V' (dot between chapter and verse),
    # not the 'Book C:V-V' shape lookup_reference/parse_reading_citation
    # produce -- normalize before querying.
    sdisplay_citation = citation.replace(':', '.', 1)

    with connection.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT r.pdist
            FROM calendarium_reading r
            JOIN calendarium_pericope p ON p.id = r.pericope_id
            WHERE r.source = 'Gospel'
              AND r.tradition IN ('common', 'slavic')
              AND r.pdist IS NOT NULL
              AND p.sdisplay = %s
        """, [sdisplay_citation])
        exact = sorted(row[0] for row in cur.fetchall())
        if exact:
            return exact

    # Fuzzy fallback: parse "Book C:V" (first verse only, ignoring
    # multi-range suffixes) and match against Pericope.verses' start code
    # ('Book_CCCVVV_CCCVVV') within a small tolerance.
    m = re.match(r'^(.+?)\s+(\d+)[:.](\d+)', citation)
    if not m:
        return []
    book, chapter, start_verse = m.group(1), int(m.group(2)), int(m.group(3))
    start_code = chapter * 1000 + start_verse

    matches = []
    for pdist, p_book, verses in _all_gospel_pericopes():
        if p_book != book:
            continue
        vm = _VERSES_RE.match(verses)
        if not vm:
            continue
        try:
            p_start = int(vm.group(2))
        except ValueError:
            continue
        if abs(p_start - start_code) <= 2:
            matches.append(pdist)
    return sorted(set(matches))


def trace_year(year, start_month_day=(11, 1), end_month_day=(2, 10)):
    gy = GreekYear(year)
    print(f'=== GreekYear({year}): nativity_weekday={_weekday_name(gy.nativity, gy)} '
          f'lukan_jump={gy.lukan_jump} ===')

    start = date(year, *start_month_day)
    end = date(year + 1, *end_month_day)

    dt = start
    while dt <= end:
        path = os.path.join(CACHE_DIR, f'{dt.isoformat()}.json')
        if not os.path.exists(path):
            dt += timedelta(days=1)
            continue

        day = json.loads(open(path).read())
        gospel_title = day.get('reading2Title') or ''
        calendar_pdist = gy.date_to_pdist(dt.month, dt.day, dt.year)

        try:
            citation = parse_reading_citation(gospel_title)
        except ValueError:
            citation = None

        # The same pericope text can recur at wildly different pdist values
        # elsewhere in the multi-year cycle table (a Saint's commons reading
        # reusing Gospel text, or the same text reused a full cycle away).
        # The drift we're chasing is always small (<= lukan_jump, at most a
        # few weeks), so only a candidate within a generous plausible window
        # counts as the real continuous-cycle match -- anything else is a
        # coincidental textual match, not evidence about the drift.
        PLAUSIBLE_WINDOW = 60
        raw_matches = content_at_pdist(citation) if citation else []
        matches = [m for m in raw_matches if abs(m - calendar_pdist) <= PLAUSIBLE_WINDOW]

        if not matches:
            offset_str = 'NO-MATCH'
        else:
            best = min(matches, key=lambda m: abs(m - calendar_pdist))
            offset = best - calendar_pdist
            offset_str = f'{offset:+d}'
            if len(matches) > 1:
                others = [m - calendar_pdist for m in matches if m != best]
                offset_str += f' (also {others})'

        print(f'{dt.isoformat()}  pdist={calendar_pdist:+4d}  '
              f'gospel={gospel_title:30s}  offset={offset_str}')

        dt += timedelta(days=1)


def _weekday_name(pdist, gy):
    from calendarium import datetools
    return datetools.weekday_from_pdist(pdist).name


if __name__ == '__main__':
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    trace_year(year)

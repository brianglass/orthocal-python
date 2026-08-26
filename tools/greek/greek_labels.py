"""Reconstruct the Greek-native lectionary from antiochian.org's own day labels.

antiochian.org's `feastDayTitle` is usually a saint's name, but on days with no
ranking commemoration it is instead the day's own *lectionary slot identity*, in
one of three formats:

    A.  "17TH TUESDAY AFTER PENTECOST"   -> Matthew section, week 17, Tuesday
    B.  "TUESDAY OF THE 15TH WEEK"       -> Luke section, week 15, Tuesday
    S.  "12TH SUNDAY OF LUKE"            -> the numbered Sunday/Saturday series

This is Greek's *own* week-numbering, independent of this project's Slavic-built
`pdist` table.  Resolving citations through it avoids the coincidental-text-reuse
noise that defeated earlier passes of the weekday-drift investigation (which
matched Greek citations against `common`/`slavic` pdist positions instead).

Writes data/greek_lectionary_from_labels.json.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative

import collections
import datetime
import glob
import json
import re

WEEKDAYS = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY']
_WD = '|'.join(WEEKDAYS)

MATTHEW_SECTION = re.compile(rf'^(\d+)(?:ST|ND|RD|TH)\s+({_WD})\s+AFTER PENTECOST$')
LUKE_SECTION = re.compile(rf'^({_WD})\s+OF THE\s+(\d+)(?:ST|ND|RD|TH)\s+WEEK$')
NUMBERED_SERIES = re.compile(r'^(\d+)(?:ST|ND|RD|TH)\s+(SUNDAY|SATURDAY) OF (MATTHEW|LUKE)$')


def load_raw():
    days = {}
    for path in sorted(glob.glob('data/antiochian_raw/*.json')):
        day = json.load(open(path))
        days[day['originalCalendarDate']] = day
    return days


def classify(title):
    """Return (section, week, weekday) for a slot label, else None."""
    title = title.upper().strip()
    if m := MATTHEW_SECTION.match(title):
        return 'matthew', int(m.group(1)), m.group(2)
    if m := LUKE_SECTION.match(title):
        return 'luke', int(m.group(2)), m.group(1)
    if m := NUMBERED_SERIES.match(title):
        return f'{m.group(3).lower()}-{m.group(2).lower()}', int(m.group(1)), None
    return None


def first_sun_luke(year):
    """2nd Sunday after the Elevation -- where Greek's Lukan jump lands."""
    elevation = datetime.date(year, 9, 14)
    first_sunday_after = elevation + datetime.timedelta(days=(6 - elevation.weekday()) % 7 or 7)
    return first_sunday_after + datetime.timedelta(days=7)


def build(days):
    """slot -> {citation: [dates]}, keeping every variant so conflicts stay visible."""
    table = collections.defaultdict(lambda: collections.defaultdict(list))
    for date, day in sorted(days.items()):
        slot = classify(day.get('feastDayTitle', ''))
        if not slot:
            continue
        for key, source in (('reading2Title', 'gospel'), ('reading1Title', 'epistle')):
            citation = day.get(key, '').strip().upper()
            if citation:
                table[(source, *slot)][citation].append(date)
    return table


def pointer_lag(days):
    """Per-cycle trace of (Luke-section week label) minus (calendar week since the jump).

    Holds at exactly -1 from the jump through Dec 31 in every harvested cycle;
    the deviations are the Nativity/Theophany suspension.
    """
    trace = collections.defaultdict(list)
    for date, day in sorted(days.items()):
        slot = classify(day.get('feastDayTitle', ''))
        if not slot or slot[0] != 'luke':
            continue
        _, week, weekday = slot
        when = datetime.date.fromisoformat(date)
        cycle = when.year if when.month >= 9 else when.year - 1
        week_one_monday = first_sun_luke(cycle) + datetime.timedelta(days=1)
        calendar_week = (when - week_one_monday).days // 7 + 1
        trace[cycle].append({
            'date': date,
            'weekday': weekday,
            'label_week': week,
            'calendar_week': calendar_week,
            'lag': calendar_week - week,
            'gospel': day.get('reading2Title', '').strip(),
        })
    return trace


def main():
    days = load_raw()
    table = build(days)

    out = {'slots': {}, 'pointer_lag': pointer_lag(days)}
    conflicts = 0
    for (source, section, week, weekday), variants in sorted(table.items()):
        key = f'{source}|{section}|{week}|{weekday or "-"}'
        ordered = sorted(variants.items(), key=lambda kv: -len(kv[1]))
        out['slots'][key] = {citation: dates for citation, dates in ordered}
        if len(ordered) > 1:
            conflicts += 1

    with open('data/greek_lectionary_from_labels.json', 'w') as f:
        json.dump(out, f, indent=1, sort_keys=True)

    print(f'{len(out["slots"])} labeled slots, {conflicts} with more than one citation')
    for cycle, rows in sorted(out['pointer_lag'].items()):
        stable = [r for r in rows if r['date'] < f'{cycle + 1}-01-01']
        lags = {r['lag'] for r in stable}
        print(f'  cycle {cycle}/{cycle + 1}: {len(stable):>3} labeled days through Dec 31, lag={lags}')


if __name__ == '__main__':
    main()

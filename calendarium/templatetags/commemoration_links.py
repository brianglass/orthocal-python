"""Link the dates a commemoration's story mentions to the day they fall on.

Stories point at other commemorations by date -- "a disciple of Saint
Anthony (January 17)", "for his life, see December 20" -- and those are dates
on the Church calendar. This turns them into links to that day's readings
page, keeping the reader's tradition and calendar.
"""
import calendar
import re
from datetime import date

from django import template
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe

from ..datetools import Calendar, julian_to_gregorian

register = template.Library()

# Spelled out rather than taken from calendar.month_name, which follows the
# process locale; the stories are English whatever the reader's language.
MONTHS = {
    'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5,
    'June': 6, 'July': 7, 'August': 8, 'September': 9, 'October': 10,
    'November': 11, 'December': 12,
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'Jun': 6, 'Jul': 7,
    'Aug': 8, 'Sept': 9, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
}
_FULL = 'January|February|March|April|May|June|July|August|September|October|November|December'
_ABBR = 'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec'

# "January 17", "Dec. 4", "July 19th", "5 August", "the 5th of August".
DATE_RE = re.compile(
    rf'\b(?:(?P<month>{_FULL}|(?:{_ABBR})\.?)\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?'
    rf'|(?P<day2>\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?(?P<month2>{_FULL}))\b'
)

# Dates that are not pointers to a commemoration, and so are left alone:
#
# "January 2, 1833" -- a historical date with a year; an event in a life.
_YEAR_AFTER = re.compile(r',?\s*(?:AD\s*)?\d{3,4}\b')
# "21-22 November", "November 21-22" -- a span of days, also an event.
_RANGE_AFTER = re.compile(r'\s*[-–—]\s*\d')
_RANGE_BEFORE = re.compile(r'\d\s*[-–—]\s*$')
# "(March 5 OC, March 18 NC)" -- explicitly calendar-qualified. Where these
# occur the app files the saint under the new-calendar date, so the Old
# Calendar date would link to a day the saint isn't on.
_CALENDAR_MARK = re.compile(
    r'\s*\(?\s*(?:OC|OS|NC|NS|O\.S\.|N\.S\.|[Oo]ld [Ss]tyle|[Nn]ew [Ss]tyle'
    r'|[Oo]ld [Cc]alendar|[Nn]ew [Cc]alendar)(?![A-Za-z])'
)

_TAG_RE = re.compile(r'(<[^>]*>)')


def _is_leap(year, calendar_kind):
    if calendar_kind == Calendar.Julian:
        return year % 4 == 0
    return calendar.isleap(year)


def link_date(month, day, church_today, calendar_kind):
    """The civil date to link to for `month`/`day` on the Church calendar,
    or None when that is the day already being viewed.

    `church_today` is the viewed day on the Church calendar: the Julian date
    for an Old Calendar reader, the civil date otherwise.

    A date links within the current Church year, which begins on September 1,
    so a page always links the same way regardless of when it is read. The
    exception is Feb 29, which links to the soonest one that hasn't passed --
    many Church years have none.
    """

    if (month, day) == (church_today.month, church_today.day):
        return None

    if (month, day) == (2, 29):
        year = church_today.year
        if (church_today.month, church_today.day) > (2, 29):
            year += 1
        while not _is_leap(year, calendar_kind):
            year += 1
    else:
        start = church_today.year if church_today.month >= 9 else church_today.year - 1
        year = start if month >= 9 else start + 1

    if calendar_kind == Calendar.Julian:
        return julian_to_gregorian(year, month, day)
    return date(year, month, day)


def _link(match, context):
    text = match.string
    before, after = text[:match.start()], text[match.end():]
    if (_YEAR_AFTER.match(after) or _RANGE_AFTER.match(after)
            or _RANGE_BEFORE.search(before) or _CALENDAR_MARK.match(after)):
        return match.group(0)

    month = MONTHS[(match['month'] or match['month2']).rstrip('.')]
    day = int(match['day'] or match['day2'])
    if not 1 <= day <= calendar.monthrange(2000, month)[1]:
        return match.group(0)

    target = link_date(month, day, context.date, context.calendar)
    if target is None:
        return match.group(0)

    url = reverse('readings', kwargs={
        'tradition': context.tradition,
        'cal': context.calendar,
        'year': target.year,
        'month': target.month,
        'day': target.day,
    })
    return f'<a class="commemoration-date" href="{escape(url)}">{match.group(0)}</a>'


@register.filter
def link_commemoration_dates(html, context):
    """Link the Church-calendar dates in a story's HTML.

    `context` needs `date` (the viewed day on the Church calendar),
    `calendar` and `tradition` -- a liturgics Day has all three. Only text
    between tags is rewritten, and never inside an existing link, so the
    story's own markup passes through untouched.
    """

    if not html:
        return html

    parts = _TAG_RE.split(html)
    in_link = False
    for i, part in enumerate(parts):
        if i % 2:
            if re.match(r'<a\b', part, re.IGNORECASE):
                in_link = True
            elif re.match(r'</a\s*>', part, re.IGNORECASE):
                in_link = False
        elif not in_link:
            parts[i] = DATE_RE.sub(lambda match: _link(match, context), part)

    return mark_safe(''.join(parts))

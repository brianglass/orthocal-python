from types import SimpleNamespace

from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from calendarium.datetools import Calendar, Tradition, cal_session_key, gregorian_to_julian
from calendarium.liturgics.day import _has_story

from .models import DayCommemoration, Saint
from .search import matching_saints

_MONTH_NAMES = [
    '', 'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
]


def _occasion_date(day):
    """A human-readable label for a fixed-calendar (month/day) occasion, or
    a Pascha-relative label for a moveable one -- there's no year-independent
    calendar date for a moveable feast, only its distance from Pascha."""

    if day.pdist == 999:
        return f'{_MONTH_NAMES[day.month]} {day.day}'
    return f'Moveable (Pascha {day.pdist:+d} days)'


def _story_link_context(request):
    """What the dates in a saint's stories link to.

    A saint page has no date of its own, so links resolve against today, on
    the calendar and tradition the reader last chose. They have to use the
    remembered calendar rather than a fixed one: the readings page remembers
    whatever calendar a URL carries, so linking an Old Calendar reader to a
    `gregorian` URL would quietly switch them to the New Calendar."""

    tradition = request.session.get('tradition', Tradition.Slavic)
    cal = request.session.get(cal_session_key(tradition), Calendar.Gregorian)
    today = timezone.localtime().date()
    if cal == Calendar.Julian:
        today = gregorian_to_julian(today.year, today.month, today.day)
    return SimpleNamespace(date=today, calendar=cal, tradition=tradition)


def _attach_display_name(saint):
    """Saint.name is backfilled from whichever DayCommemoration happened to
    be used when the row was created, which is often occasion-specific
    ("Repose of...", "Uncovering of the relics of...") rather than the
    saint's plain identity. full_name is usually the cleaner form when it's
    set (see the Saint model's own docstring) -- prefer it for display."""

    saint.display_name = saint.full_name or saint.name
    return saint


def search_view(request):
    query = request.GET.get('q', '').strip()
    results = []

    if query:
        candidates = matching_saints(query).prefetch_related('daycommemoration_set__day').order_by('name')[:50]
        for saint in candidates:
            dcs = list(saint.daycommemoration_set.all())
            # A saint with no story on any commemoration has nothing to show
            # on the detail page -- still worth listing (it confirms they
            # exist and disambiguates from same-named saints who do have a
            # page), but the template renders it unlinked rather than as a
            # dead end. Every result shows its date(s) -- a saint can have
            # more than one commemoration (e.g. a main entry and a separate
            # relics-related one), so this is a list, not a single date.
            saint.has_story = any(_has_story(dc) for dc in dcs)
            sorted_dcs = sorted(dcs, key=lambda dc: (dc.day.month, dc.day.day))
            saint.occasion_dates = ', '.join(_occasion_date(dc.day) for dc in sorted_dcs)
            results.append(_attach_display_name(saint))

        # A single match with somewhere to go is unambiguous -- skip
        # straight to their page rather than making the user click through
        # a one-item list. A single story-less match has no page to redirect
        # to, so it's shown (unlinked) same as any other story-less result.
        # Not for htmx's live-as-you-type requests, though -- redirecting
        # mid-keystroke the moment a query narrows to one match would yank
        # the page out from under someone who hasn't finished typing yet.
        if len(results) == 1 and results[0].has_story and request.headers.get('HX-Request') != 'true':
            return redirect('saint-detail', results[0].slug)

    return render(request, 'saint_search.html', context={
        'query': query,
        'results': results,
    })


def saint_detail_view(request, slug):
    saint = _attach_display_name(get_object_or_404(Saint, slug=slug))

    commemorations = list(
        DayCommemoration.objects.filter(saints=saint)
        .select_related('day')
        .order_by('day__month', 'day__day')
    )

    for dc in commemorations:
        dc.date_display = _occasion_date(dc.day)
        dc.has_story = _has_story(dc)

    return render(request, 'saint_detail.html', context={
        'saint': saint,
        'commemorations': commemorations,
        'story_links': _story_link_context(request),
    })

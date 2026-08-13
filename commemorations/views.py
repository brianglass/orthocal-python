from django.shortcuts import get_object_or_404, redirect, render

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
        candidates = matching_saints(query).prefetch_related('daycommemoration_set').order_by('name')
        for saint in candidates:
            # A result with no story on any of its commemorations is a dead
            # end -- the detail page would show only bare titles and dates,
            # nothing worth clicking through for.
            if any(_has_story(dc) for dc in saint.daycommemoration_set.all()):
                results.append(_attach_display_name(saint))
                if len(results) >= 50:
                    break

        # A single match is unambiguous -- skip straight to their page
        # rather than making the user click through a one-item list.
        if len(results) == 1:
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
    })

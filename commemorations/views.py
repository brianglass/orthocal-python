from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from calendarium.liturgics.day import _has_story

from .models import DayCommemoration, Saint
from .transliteration import normalize_transliteration

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
        # Each term must match somewhere (name, full_name, or a linked
        # commemoration's title), but not all in the same field or the same
        # word order -- e.g. "John Theologian" should still find "St. John
        # the Theologian" even though "John Theologian" is never a
        # contiguous substring of that name.
        term_filter = Q()
        for term in query.split():
            term_filter &= (
                Q(name__icontains=term)
                | Q(full_name__icontains=term)
                | Q(daycommemoration__title__icontains=term)
                | Q(normalized_name__icontains=normalize_transliteration(term))
            )

        results = [
            _attach_display_name(saint)
            for saint in Saint.objects.filter(term_filter).distinct().order_by('name')[:50]
        ]

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

from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from calendarium.liturgics.day import _has_story

from .models import DayCommemoration, Saint

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


def search_view(request):
    query = request.GET.get('q', '').strip()
    results = []

    if query:
        results = list(
            Saint.objects.filter(
                Q(name__icontains=query)
                | Q(full_name__icontains=query)
                | Q(daycommemoration__title__icontains=query)
            ).distinct().order_by('name')[:50]
        )

    return render(request, 'saint_search.html', context={
        'query': query,
        'results': results,
    })


def saint_detail_view(request, pk):
    saint = get_object_or_404(Saint, pk=pk)

    commemorations = list(
        DayCommemoration.objects.filter(saint=saint)
        .select_related('day')
        .order_by('day__month', 'day__day')
    )

    for dc in commemorations:
        dc.date_display = _occasion_date(dc.day)

    stories = [dc for dc in commemorations if _has_story(dc)]

    return render(request, 'saint_detail.html', context={
        'saint': saint,
        'commemorations': commemorations,
        'stories': stories,
    })

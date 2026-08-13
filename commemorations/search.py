from django.db.models import Exists, OuterRef, Q

from .models import DayCommemoration, Saint
from .transliteration import normalize_transliteration


def _term_filter(term):
    """Q filter for Saint objects matching a single search term via name,
    full_name, normalized_name (transliteration-aware), or a linked
    commemoration's title.

    A title match only counts if no saint linked to that commemoration
    specifically owns the term in their own name/full_name -- e.g.
    "Chrysostom" is Chrysostom's own word (Basil and Gregory don't get
    credit for their shared "Synaxis of the Three Holy Hierarchs"
    commemoration just because his name is in its title), but "Three" or
    "Hierarchs" isn't any of the three's own word, so it's a genuinely
    shared term and all three should match on it."""

    term_owned_by_a_linked_saint = Saint.objects.filter(
        daycommemoration=OuterRef('pk'),
    ).filter(Q(name__icontains=term) | Q(full_name__icontains=term))
    shared_title_match = DayCommemoration.objects.filter(
        saints=OuterRef('pk'), title__icontains=term,
    ).exclude(Exists(term_owned_by_a_linked_saint))

    return (
        Q(name__icontains=term)
        | Q(full_name__icontains=term)
        | Q(normalized_name__icontains=normalize_transliteration(term))
        | Exists(shared_title_match)
    )


def matching_saints(query):
    """Saint queryset matching query -- each whitespace-separated term must
    match somewhere (not all in the same field or the same word order), so
    e.g. "John Theologian" still finds "St. John the Theologian" even
    though that's never a contiguous substring of the name."""

    term_filter = Q()
    for term in query.split():
        term_filter &= _term_filter(term)
    return Saint.objects.filter(term_filter).distinct()

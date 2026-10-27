import re

from dataclasses import dataclass

from django.db import connection
from django.db.models import Exists, OuterRef, Q
from django.utils.html import escape

from .models import DayCommemoration, Saint
from .transliteration import normalize_transliteration

# An FTS5 table with one row per DayCommemoration (rowid = its pk): the
# title, the linked saints' names, and the life as plain text. Created by
# migration 0018 and filled by the build_saint_search_index command.
LIFE_SEARCH_TABLE = 'commemorations_life_search'

# Marks the matched words in an excerpt. Control characters can't occur in
# the lives, so they survive HTML escaping and can be swapped for markup
# afterwards.
_HIT_START, _HIT_END = '\x02', '\x03'


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

    # Word-boundary, not icontains -- normalize_transliteration shortens some
    # words enough (e.g. "Mary" -> "mari") that a plain substring match
    # would false-positive against unrelated names that happen to start the
    # same way ("Marinus", "Marina", "Mariamne"). The normalized field only
    # exists to match whole transliterated names/tokens against each other,
    # so it never needed substring matching in the first place.
    normalized_term = re.escape(normalize_transliteration(term))

    return (
        Q(name__icontains=term)
        | Q(full_name__icontains=term)
        | Q(normalized_name__iregex=rf'\b{normalized_term}\b')
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


@dataclass
class LifeMatch:
    commemoration_id: int
    excerpt: str  # the matched words are wrapped in _HIT_START/_HIT_END

    def excerpt_html(self):
        return escape(self.excerpt).replace(_HIT_START, '<mark>').replace(_HIT_END, '</mark>')

    def excerpt_text(self):
        return self.excerpt.replace(_HIT_START, '').replace(_HIT_END, '')


def _fts_query(query, prefix):
    """An FTS5 query requiring every word in query, or None if it has none.

    Each word is quoted, so punctuation and FTS5's own operators (AND, NOT,
    NEAR, column filters) in what someone typed are taken literally rather
    than as syntax. With prefix, the last word also matches as the start of
    a longer one, for search-as-you-type -- but not under three letters,
    where it would match nearly everything."""

    words = re.findall(r'\w+', query)
    if not words:
        return None

    terms = [f'"{word}"' for word in words]
    if prefix and len(words[-1]) >= 3:
        terms[-1] += '*'
    return ' '.join(terms)


def matching_lives(query, prefix=False, limit=50):
    """LifeMatch for each commemoration with a life that matches query, best
    first.

    Every word must appear in the commemoration's title, its saints' names
    or its life, so "Cosmas physician" finds the Unmercenaries even though
    "Cosmas" is only in their names. Words are stemmed ("healed" finds
    "healing") and accents are ignored. Titles and names count for more
    than the life when ranking, and the excerpt always comes from the
    life."""

    fts_query = _fts_query(query, prefix)
    if fts_query is None:
        return []

    with connection.cursor() as cursor:
        cursor.execute(
            f'''SELECT rowid, snippet({LIFE_SEARCH_TABLE}, 2, %s, %s, '…', 24)
                FROM {LIFE_SEARCH_TABLE}
                WHERE {LIFE_SEARCH_TABLE} MATCH %s AND story != ''
                ORDER BY bm25({LIFE_SEARCH_TABLE}, 4.0, 4.0, 1.0)
                LIMIT %s''',
            [_HIT_START, _HIT_END, fts_query, limit],
        )
        return [LifeMatch(pk, excerpt) for pk, excerpt in cursor.fetchall()]

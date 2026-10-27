import difflib
import functools
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
# Every distinct word in LIFE_SEARCH_TABLE, as indexed (lowercase, stemmed,
# without accents).
LIFE_SEARCH_VOCABULARY = 'commemorations_life_search_vocab'

# Endings that turn a place into its people: Cappadocia -> Cappadocian,
# Egypt -> Egyptian, Antioch -> Antiochian. Stemming doesn't relate the two,
# and the lives mostly name the place.
_PEOPLE_ENDINGS = ('n', 'an', 'ian', 'ns', 'ans', 'ians')

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


@functools.cache
def vocabulary():
    """Every distinct word in the index. Cached per process, since the
    index is built into the image; build_saint_search_index clears it."""

    with connection.cursor() as cursor:
        cursor.execute(f'SELECT term FROM {LIFE_SEARCH_VOCABULARY}')
        return frozenset(term for term, in cursor.fetchall())


def _people_forms(word):
    """word's place and people forms that occur in the index, for instance
    {'cappadocia'} for "Cappadocian", or {'egyptian'} for "Egypt"."""

    word = word.lower()
    pairs = {(word, word + ending) for ending in _PEOPLE_ENDINGS}
    pairs |= {
        (word[:-len(ending)], word) for ending in _PEOPLE_ENDINGS
        if word.endswith(ending) and len(word) - len(ending) >= 4
    }
    # A place ending in n doesn't take -ian: "Roman" and "Romanian" aren't
    # a place and its people.
    forms = {
        people if place == word else place
        for place, people in pairs
        if not (place.endswith('n') and people[len(place):].startswith('i'))
    }
    return forms & vocabulary() if len(word) >= 4 else set()


def _fts_query(query, prefix):
    """An FTS5 query requiring every word in query, or None if it has none.

    Each word is quoted, so punctuation and FTS5's own operators (AND, NOT,
    NEAR, column filters) in what someone typed are taken literally rather
    than as syntax. A word also matches its place or people form (see
    _PEOPLE_ENDINGS). With prefix, the last word also matches as the start
    of a longer one, for search-as-you-type -- but not under three letters,
    where it would match nearly everything."""

    words = re.findall(r'\w+', query)
    if not words:
        return None

    terms = []
    for n, word in enumerate(words):
        star = '*' if prefix and n == len(words) - 1 and len(word) >= 3 else ''
        forms = [f'"{word}"{star}'] + [f'"{form}"' for form in sorted(_people_forms(word))]
        terms.append(forms[0] if len(forms) == 1 else f'({" OR ".join(forms)})')
    return ' AND '.join(terms)


def _in_index(word):
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT 1 FROM {LIFE_SEARCH_TABLE} WHERE {LIFE_SEARCH_TABLE} MATCH %s LIMIT 1', [f'"{word}"'])
        return cursor.fetchone() is not None


def corrected_query(query):
    """query with each word the index doesn't know replaced by the closest
    one it does ("Cappdocian" -> "cappadocian"), or None if no word needed
    correcting or none had a close match. For when a search finds nothing.

    The replacements are words as indexed, so they are lowercase and may be
    stemmed."""

    words = re.findall(r'\w+', query)
    corrected = []
    for word in words:
        if len(word) >= 4 and not _in_index(word):
            if close := difflib.get_close_matches(word.lower(), vocabulary(), n=1, cutoff=0.8):
                corrected.append(close[0])
                continue
        corrected.append(word)

    return ' '.join(corrected) if corrected != words else None


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

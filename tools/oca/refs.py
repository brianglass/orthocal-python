"""Canonicalise a scripture citation to a comparable token.

Lifted from tools/greek/three_way.py, which is where it was worked out. Two
traps are baked in and both cost real time when they were missing:

  * **Ordinal position varies by source.** oca.org writes "1 Timothy", GOA
    writes "I Corinthians", antiochian.org writes "St Peter's First Universal
    Letter". The ordinal has to be read from words *and* numerals *and* Roman
    numerals, on either side of the book name. Getting this wrong inflated one
    audit's difference count from 4 to 16.
  * **Jude and Philemon have one chapter**, so sources cite them bare
    ("Jude 1-10", not "Jude 1:1-10"). Without special-casing, a stray leading
    numeral gets read as an ordinal and the verse as a chapter.

canon() returns a token like "1TIM3:14" -- book plus *opening* chapter:verse.
Openings alone are deliberately not enough to call two readings equal; see
near(), and the closing-reference check in tools/greek/load_ordo.py.
"""
import re

BOOKS = [
    ('GEN', r'GENESIS|GEN'), ('EX', r'EXODUS|EXOD?'), ('LEV', r'LEVITICUS|LEV'),
    ('NUM', r'NUMBERS|NUM'), ('DEUT', r'DEUTERONOMY|DEUT'), ('JOSH', r'JOSHUA|JOSH'),
    ('JUDG', r'JUDGES|JUDG'), ('SAM', r'SAMUEL|SAM|KINGDOMS'), ('KGS', r'KINGS|KGS'),
    ('CHR', r'CHRONICLES|CHRON'), ('JOB', r'JOB'), ('PS', r'PSALMS?|PS'),
    ('PROV', r'PROVERBS|PROV'), ('ECCL', r'ECCLESIASTES|ECCL'), ('SONG', r'SONG'),
    ('WIS', r'WISDOM|WIS'), ('SIR', r'SIRACH|ECCLESIASTICUS'), ('ISA', r'ISAIAH|ISA'),
    ('JER', r'JEREMIAH|JER'), ('EZEK', r'EZEKIEL|EZEK'), ('DAN', r'DANIEL|DAN'),
    ('HOS', r'HOSEA'), ('JOEL', r'JOEL'), ('AMOS', r'AMOS'), ('JONAH', r'JONAH'),
    ('MIC', r'MICAH'), ('ZEPH', r'ZEPHANIAH'), ('ZECH', r'ZECHARIAH'), ('MAL', r'MALACHI'),
    ('MATT', r'MATTHEW|MATT'), ('MARK', r'MARK'), ('LUKE', r'LUKE'), ('JOHN', r'JOHN'),
    ('ACTS', r'ACTS'), ('ROM', r'ROMANS|ROM'), ('COR', r'CORINTHIANS|COR'),
    ('GAL', r'GALATIANS|GAL'), ('EPH', r'EPHESIANS|EPH'), ('PHIL', r'PHILIPPIANS|PHIL'),
    ('COL', r'COLOSSIANS|COL'), ('THESS', r'THESSALONIANS|THESS'), ('TIM', r'TIMOTHY|TIM'),
    ('TITUS', r'TITUS'), ('PHLM', r'PHILEMON|PHLM'), ('HEB', r'HEBREWS|HEB'),
    ('JAS', r'JAMES|JAS'), ('PET', r'PETER|PET'), ('JUDE', r'JUDE'), ('REV', r'REVELATION|REV'),
]
# JOHN must lose to the epistles' ordinals but win over nothing; order matters
# only through the leftmost-match rule in canon().
BOOK_RE = [(t, re.compile(rf'\b(?:{p})\b')) for t, p in BOOKS]

SINGLE_CHAPTER = ('JUDE', 'PHLM')


COMPOSITE = re.compile(r'Composite\s+(\d+)')


def canon(s):
    """"1 Timothy 3:14-4:5" -> "1TIM3:14". Empty string if unparseable."""
    if not s:
        return ''

    # Composites are named, not cited. oca.org prints "Composite 17 - Exodus
    # 40" and this repo "Composite 17 - Exodus 40:1-5, 9-10, 16, 34-35", so
    # neither the chapter nor the verses can be relied on to agree -- oca.org
    # often gives no verse at all, which would make the citation unparseable
    # and the app's resolved reference look spurious. Both sides carry the same
    # number, and that number is the identity.
    m = COMPOSITE.search(s)
    if m:
        return f'COMP{m.group(1)}'
    u = re.sub(r'[^A-Z0-9:; ,\-]', ' ', s.upper().replace('.', ':'))
    hit = min(((m.start(), t) for t, rx in BOOK_RE if (m := rx.search(u))), default=None)
    if hit is None:
        return ''
    pos, book = hit

    ordinal = ''
    for word, digit in (('THIRD', '3'), ('SECOND', '2'), ('FIRST', '1')):
        if re.search(rf'\b{word}\b', u):
            ordinal = digit
            break
    if not ordinal:
        m = re.search(r'\b(I{1,3}|[123])\s*$', u[:pos].strip() + ' ')
        if m:
            ordinal = m.group(1) if m.group(1).isdigit() else str(len(m.group(1)))
    if book in SINGLE_CHAPTER:
        ordinal = ''

    tail = u[pos:]
    m = re.search(r'(\d+):(\d+)', tail)
    if m:
        return f'{ordinal}{book}{m.group(1)}:{m.group(2)}'
    if book in SINGLE_CHAPTER:
        m = re.search(r'(\d+)', tail)
        if m:
            return f'{ordinal}{book}1:{m.group(1)}'
    return ''


GOSPELS = {'MATT', 'MARK', 'LUKE', 'JOHN'}
EPISTLES = {'ACTS', 'ROM', 'COR', 'GAL', 'EPH', 'PHIL', 'COL', 'THESS', 'TIM',
            'TITUS', 'PHLM', 'HEB', 'JAS', 'PET', 'JUDE', 'JOHN', 'REV'}


def slot(token):
    """Which liturgical slot a canon() token belongs to: Gospel, Epistle or OT.

    Derived from the book, never from a citation's position in a table.
    oca.org's monthly tables are not positionally stable -- February through
    April carry an extra column, and a Lenten day's two Old Testament lessons
    sit in the cells a Liturgy day uses for Epistle and Gospel. Reading the
    slot off the column number silently swaps Epistle and Gospel for a third of
    the year.

    The ordinal is what separates the two Johns: "JOHN3:16" is the Gospel,
    "1JOHN1:8" is the epistle.
    """
    m = re.match(r'^(\d?)([A-Z]+)\d+:\d+$', token or '')
    if not m:
        return None
    ordinal, book = m.group(1), m.group(2)
    if book in GOSPELS and not ordinal:
        return 'Gospel'
    if book in EPISTLES:
        return 'Epistle'
    return 'OT'


def classify(citation):
    """The slot of a raw citation, even when it carries no chapter:verse.

    canon() needs a chapter and verse, which the composite Vespers lessons do
    not have -- "Composite 2 - Proverbs 10, 3, 8" names three chapters of
    Proverbs and no verse at all. There are 38 such rows and every one is an
    Old Testament Vespers lesson, so falling back to the book name alone
    classifies them correctly even though they can never be matched by citation.
    """
    token = canon(citation)
    if token and not token.startswith('COMP'):
        return slot(token)
    # A composite token carries no book, so fall through to the book name in
    # the citation text -- "Composite 2 - Proverbs 10, 3, 8" is an OT lesson.

    u = re.sub(r'[^A-Z0-9:; ,\-]', ' ', (citation or '').upper().replace('.', ':'))
    hit = min(((m.start(), t) for t, rx in BOOK_RE if (m := rx.search(u))), default=None)
    if hit is None:
        return None
    pos, book = hit
    ordinal = bool(re.search(r'\b(I{1,3}|[123]|FIRST|SECOND|THIRD)\s*$', u[:pos].strip() + ' '))
    if book in GOSPELS and not ordinal:
        return 'Gospel'
    if book in EPISTLES:
        return 'Epistle'
    return 'OT'


def near(a, b, tolerance=2):
    """Same book and chapter, opening verse within `tolerance`.

    The traditions genuinely differ by a verse or two at some pericope
    boundaries -- this repo has `Matt 22.1-14` where both Greek jurisdictions
    print `22:2-14`. Tolerating that is necessary; tolerating much more is not,
    because distinct pericopes can open two verses apart.
    """
    if a == b:
        return True
    if not a or not b:
        return False
    pa, pb = (re.match(r'^(\d?[A-Z]+)(\d+):(\d+)$', x) for x in (a, b))
    if not (pa and pb):
        return False
    return (pa.group(1) == pb.group(1)
            and pa.group(2) == pb.group(2)
            and abs(int(pa.group(3)) - int(pb.group(3))) <= tolerance)

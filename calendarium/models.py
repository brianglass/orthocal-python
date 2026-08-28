import re

from django.db import models
from django.utils.functional import cached_property

from bible.models import Verse

# pdist is the distance between the given day and Pascha for the current calendar year
# pdist values >= 1000 are for floats and are programmatically mapped
# Rows with pdist == 999 are for days on the fixed calendar (e.g. Menaion)
# Rows with pdist in the 701-711 range are Matins gospels


class Day(models.Model):
    pdist = models.SmallIntegerField(db_index=True)
    month = models.SmallIntegerField()
    day = models.SmallIntegerField()
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=128)
    feast_name = models.CharField(max_length=255)
    feast_level = models.SmallIntegerField()
    service = models.SmallIntegerField()
    service_note = models.CharField(max_length=64)
    story = models.TextField(null=True, blank=True)  # feast-level narrative, non-saint content
    fast = models.SmallIntegerField()
    fast_exception = models.SmallIntegerField()
    flag = models.SmallIntegerField()
    tradition = models.CharField(max_length=16, choices=[
        ('common', 'Common'),  # shared by all traditions (the default)
        ('slavic', 'Slavic-specific'),
        ('greek', 'Greek-specific'),
    ], default='common')

    def __str__(self):
        return self.full_title

    @cached_property
    def full_title(self):
        return f'{self.title}: {self.subtitle}' if self.subtitle else self.title

    class Meta:
        indexes = [models.Index(fields=('month', 'day'))]


class Reading(models.Model):
    # Ordering field
    #
    # 1-99 lenten matins
    # 100+ 1st hour (lent)
    # 200+ 3rd hour
    # 300+ 6th hour
    # 400+ 9th hour
    # 500+ lenten vespers
    # 600+ vespers
    # 700+ matins
    # 800+ liturgy epistles
    # 900+ liturgy gospels
    # 100+ post-liturgy

    month = models.SmallIntegerField()
    day = models.SmallIntegerField()
    pdist = models.SmallIntegerField(db_index=True)
    source = models.CharField(max_length=64)
    desc = models.CharField(max_length=64)
    pericope = models.ForeignKey('Pericope', on_delete=models.CASCADE)
    ordering = models.SmallIntegerField()
    flag = models.SmallIntegerField()
    tradition = models.CharField(max_length=16, choices=[
        ('common', 'Common'),  # shared by all traditions (the default)
        ('slavic', 'Slavic-specific'),
        ('greek', 'Greek-specific'),
    ], default='common')

    class Meta:
        indexes = [models.Index(fields=('month', 'day'))]

    async def aget_pericope(self):
        # Using self.pericope only works synchronously.
        return await Pericope.objects.aget(id=self.pericope_id)


class Pericope(models.Model):
    pericope = models.CharField(max_length=8)
    book = models.CharField(max_length=16)
    display = models.CharField(max_length=128)
    sdisplay = models.CharField(max_length=64)
    desc = models.CharField(max_length=128)
    preverse = models.CharField(max_length=8)
    prefix = models.CharField(max_length=255)
    prefixb = models.CharField(max_length=128)
    verses = models.CharField(max_length=128)
    suffix = models.CharField(max_length=255)
    flag = models.SmallIntegerField()

    class Meta:
        unique_together = 'pericope', 'book'

    def __str__(self):
        return self.display

    async def aget_passage(self, language='en', translation=None):
        try:
            return self.passage
        except AttributeError:
            self.passage = [verse async for verse in self.get_passage(language=language, translation=translation)]
            return self.passage

    def get_passage(self, language='en', translation=None):
        # Two pericopes -- Composite 17 and 18, the Entrance of the Theotokos
        # Vespers lessons -- carry a deliberate zero-width space (U+200B) in
        # front of "Composite" so this match FAILS and they fall through to the
        # scripture lookup below. It is invisible on the page and it is load
        # bearing; do not "clean" it out of the fixture.
        #
        # It is a stopgap, not a design. The Composite table has no rows 17 or
        # 18, and d4d5d54 (Nov 2023) moved a hardcoded `not in ('17', '18')`
        # out of this function and into the data. Approximating them with a
        # reference works only because these two happen to have exact verse
        # ranges; a real composite is the better representation and should
        # replace this if the text is ever obtained. Composites frequently
        # cannot be expressed as a reference at all -- Composite 24 is
        # Leviticus 26:3-12, 14-17, 19-20, 22, 33, 23-25, which runs verse 33
        # *before* 23-25 -- which is the whole reason the table exists.
        #
        # Why 17 and 18 are missing: they are the Slavic propers for that feast
        # (Exodus 40; 3 Kingdoms 7-8). The composites we do have come from
        # Archimandrite Ephrem Lash's Prophetologion, and his book assigns the
        # Greek Marian set to the Entrance instead -- Genesis 28, Ezekiel 43,
        # Proverbs 9 -- so these two readings simply are not in it. Only the
        # Ezekiel overlaps, which is why it alone is a plain reference here.
        match = re.match(r'Composite (\d+)', self.display)
        if match:
            return Composite.objects.filter(
                    composite_num=match.group(1)
            ).annotate(
                    # Make the composite look like a Verse instance. Composite
                    # readings only have one hardcoded content column,
                    # regardless of the requested translation. That text is
                    # Archimandrite Ephrem Lash's, not KJV as this comment
                    # previously said -- see ~/src/anastasis.
                    book=models.Value(''),
                    chapter=models.Value(1),
                    verse=models.Value(1),
                    language=models.Value('en'),
                    translation=models.Value('kjv'),
                    paragraph_start=models.Value(True),
            )
        else:
            return Verse.objects.lookup_reference(self.sdisplay, language=language, translation=translation)


class Composite(models.Model):
    composite_num = models.SmallIntegerField(primary_key=True)
    content = models.TextField()


class OrdoReading(models.Model):
    """A reading assigned by a jurisdiction's published annual ordo.

    A small set of days carry commemorations whose Menaion entries supply one
    reading but not the other, leaving the empty slot to whatever that year's
    ordo assigns. Those assignments are not computable from any cycle -- see
    docs/greek-lectionary.md, which establishes it directly: past its
    published Kanonion horizon goarch.org's own software stops assigning these
    days and falls back to a commons reading, which matches the curated ordo in
    1 of 15 sampled years.

    So this is a deliberate per-year overlay, the only one in this project. It
    is small (a couple of dates per jurisdiction per year) and bounded, and it
    needs extending as each jurisdiction publishes its annual ordo. Rows are
    keyed by calendar date rather than pdist because that is how an ordo is
    published.

    `pdist` points at the Reading rows to use instead of whatever the cycle
    would have selected, so the ordo *replaces* the computed reading rather
    than being listed beside it, and no synthetic Reading rows are needed.
    """

    jurisdiction = models.CharField(max_length=16, choices=[
        ('greek', 'Greek (GOA)'),
        ('antiochian', 'Antiochian'),
    ])
    year = models.SmallIntegerField()
    month = models.SmallIntegerField()
    day = models.SmallIntegerField()
    source = models.CharField(max_length=64)   # 'Gospel' or 'Epistle'
    pdist = models.SmallIntegerField()
    note = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('jurisdiction', 'year', 'month', 'day', 'source'),
                name='unique_ordo_reading',
            ),
        ]
        indexes = [models.Index(fields=('jurisdiction', 'year', 'month', 'day'))]

    def __str__(self):
        return f'{self.jurisdiction} {self.year}-{self.month:02d}-{self.day:02d} {self.source} -> pdist {self.pdist}'

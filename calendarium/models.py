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
        ('antiochian', 'Antiochian-specific'),
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
        ('antiochian', 'Antiochian-specific'),
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
        match = re.match(r'Composite (\d+)', self.display)
        if match:
            return Composite.objects.filter(
                    composite_num=match.group(1)
            ).annotate(
                    # Make the composite look like a Verse instance. Composite
                    # readings only have one hardcoded (KJV-sourced) content
                    # column, regardless of the requested translation.
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
    docs/greek-weekday-drift.md, which establishes it directly: past its
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

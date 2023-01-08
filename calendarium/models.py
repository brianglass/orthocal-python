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
    saint = models.CharField(max_length=128)
    fast = models.SmallIntegerField()
    fast_exception = models.SmallIntegerField()
    flag = models.SmallIntegerField()

    def __str__(self):
        return self.full_title

    @cached_property
    def full_title(self):
        return f'{self.title}: {self.subtitle}' if self.subtitle else self.title

    class Meta:
        index_together = 'month', 'day'


class Reading(models.Model):
    month = models.SmallIntegerField()
    day = models.SmallIntegerField()
    pdist = models.SmallIntegerField(db_index=True)
    source = models.CharField(max_length=64)
    desc = models.CharField(max_length=64)
    book = models.CharField(max_length=8)
    pericope = models.CharField(max_length=8)
    ordering = models.SmallIntegerField()
    flag = models.SmallIntegerField()

    class Meta:
        index_together = 'month', 'day'

    def get_pericopes(self):
        return Pericope.objects.filter(book=self.book, pericope=self.pericope)


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
        index_together = 'book', 'pericope'

    def __str__(self):
        return self.display

    def get_passage(self):
        match = re.match('Composite (\d+)', self.display)
        if match:
            return Composite.objects.filter(
                    composite_num=match.group(1)
            ).annotate(
                    # Make the composite look like a Verse instance.
                    book=models.Value(''),
                    chapter=models.Value(1),
                    verse=models.Value(1),
                    language=models.Value('en'),
            )
        else:
            return Verse.objects.lookup_reference(self.sdisplay)


class Composite(models.Model):
    composite_num = models.SmallIntegerField(primary_key=True)
    content = models.TextField()

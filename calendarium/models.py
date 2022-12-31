from django.db import models

# pdist is the distance between the given day and Pascha
# pdist values >= 1000 are for floats and are programmatically mapped
# Rows with pdist == 999 are for days on the fixed calendar (e.g. Menaion)
# Rows with pdist in the 701-711 range are Matins gospels


class Day(models.Model):
    # rowid = models.IntegerField(primary_key=True)
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
        return f'{self.title}: {self.subtitle}'

    def get_title(self):
        if self.subtitle:
            return f'{self.title}: {self.subtitle}'
        else:
            return self.title

    class Meta:
        # managed = False
        # db_table = 'days'
        index_together = 'month', 'day'


class Pericope(models.Model):
    # rowid = models.IntegerField(primary_key=True)
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
        # managed = False
        # db_table = 'pericopes'
        index_together = 'book', 'pericope'

    def __str__(self):
        return self.display


class Reading(models.Model):
    # rowid = models.IntegerField(primary_key=True)
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
        # managed = False
        # db_table = 'readings'
        index_together = 'month', 'day'

    def get_pericopes(self):
        return Pericope.objects.filter(book=self.book, pericope=self.pericope)


class Composite(models.Model):
    composite_num = models.SmallIntegerField(primary_key=True)
    reading = models.TextField()

    #class Meta:
    #   managed = False
    #   db_table = 'composites'

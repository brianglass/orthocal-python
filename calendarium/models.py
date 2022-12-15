from django.db import models


class Day(models.Model):
    pdist = models.SmallIntegerField()
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


class Reading(models.Model):
    month = models.SmallIntegerField()
    day = models.SmallIntegerField()
    pdist = models.SmallIntegerField()
    source = models.CharField(max_length=64)
    desc = models.CharField(max_length=64)
    book = models.CharField(max_length=8)
    pericope = models.CharField(max_length=8)
    ordering = models.SmallIntegerField()
    flag = models.SmallIntegerField()


class Composite(models.Model):
    composite_num = models.SmallIntegerField()
    reading = models.TextField()

from django.db import models


class Commemoration(models.Model):
    title = models.CharField(max_length=200)
    alt_title = models.CharField(max_length=200, null=True)
    high_rank = models.BooleanField()
    month = models.SmallIntegerField(db_index=True)
    day = models.SmallIntegerField(db_index=True, null=True, blank=True)
    story = models.TextField(null=True, blank=True)
    ordering = models.SmallIntegerField()

    class Meta:
        unique_together = 'month', 'day', 'title'
        ordering = 'ordering',

    def __repr__(self):
        return f'<Commemoration: {self.title}>'

from django.db import models


class Saint(models.Model):
    name = models.CharField(max_length=200)
    story = models.TextField(null=True, blank=True)

    def __repr__(self):
        return f'<Saint: {self.name}>'

    def __str__(self):
        return self.name

    @property
    def title(self):
        """Alias for name -- lets Saint stand in for the old Commemoration
        objects in day.stories without touching template/alexa call sites."""
        return self.name


class DayCommemoration(models.Model):
    """Links a Saint to a specific occurrence on the fixed calendar (a
    calendarium.Day row) -- e.g. a repose, a translation of relics, a
    synaxis, or a glorification. rank and new_style describe that specific
    occurrence, not the saint overall, since the same saint can have
    occurrences that differ in both (see docs/saint-model-refactor.md).

    day_native is True when this occurrence corresponds to an entry in
    Day.saints (ordering is then that entry's list position, so display
    order matches); False for commemorations that only ever existed in the
    abbamoses story corpus with no terse Day.saints counterpart (ordering
    is then the original abbamoses ordering)."""

    day = models.ForeignKey('calendarium.Day', on_delete=models.CASCADE)
    saint = models.ForeignKey(Saint, on_delete=models.CASCADE)
    rank = models.SmallIntegerField(default=0)
    new_style = models.BooleanField(default=False)
    day_native = models.BooleanField(default=True)
    ordering = models.SmallIntegerField(default=0)

    class Meta:
        unique_together = 'day', 'saint'
        ordering = 'ordering',

    def __repr__(self):
        return f'<DayCommemoration: {self.saint.name}>'


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

from django.db import models


class Saint(models.Model):
    """A person, independent of any specific commemoration occasion. Kept
    deliberately minimal -- name is the stable identity that lets multiple
    DayCommemoration occurrences (repose, translation of relics,
    glorification, etc.) be recognized as the same saint; full_name is a
    fuller descriptive form (epithet/see/office) for the eventual saint
    detail page, when we have one richer than the terse Day.saints name.
    Occasion-specific display text and narrative live on DayCommemoration,
    not here -- see docs/saint-model-refactor.md."""

    name = models.CharField(max_length=200)
    full_name = models.CharField(max_length=200, null=True, blank=True)
    # Not auto-generated on save() -- backfilled by the
    # backfill_saint_slugs management command, which runs after fixture
    # loading (see Dockerfile) so it can see this saint's commemorations
    # (for the disambiguating date) and every other saint's slug (for
    # collision checking) already in the database. null (not '') so
    # multiple not-yet-backfilled rows don't collide on the unique
    # constraint before that command runs.
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True)

    def __repr__(self):
        return f'<Saint: {self.name}>'

    def __str__(self):
        return self.name


class DayCommemoration(models.Model):
    """Links a Saint to a specific occurrence on the fixed calendar (a
    calendarium.Day row) -- e.g. a repose, a translation of relics, a
    synaxis, or a glorification. title, story, rank, high_rank, and
    new_style all describe that specific occurrence, not the saint overall,
    since the same saint can have occurrences that differ in wording,
    narrative, rank, and calendar semantics (see
    docs/saint-model-refactor.md).

    rank (Paul Kachur's daSlevel -- typikon service-structure symbol) and
    high_rank (abbamoses's own editorial "story-worthy" judgment) are
    deliberately independent fields, not one derived from the other -- see
    the Fast-follow section of docs/saint-model-refactor.md for why a
    computed property didn't hold up empirically.

    day_native is True when this occurrence corresponds to an entry in
    Day.saints (ordering is then that entry's list position, so display
    order matches); False for commemorations that only ever existed in the
    abbamoses story corpus with no terse Day.saints counterpart (ordering
    is then the original abbamoses ordering).

    tradition mirrors calendarium.Day/Reading's sparse-overlay pattern, but
    at the individual-commemoration level rather than the whole Day row --
    a tradition-specific commemoration is additive on top of the day's
    common ones, not a wholesale replacement of them (see
    docs/saint-model-refactor.md, Stage 6).

    saint is nullable for commemorations of a relic, icon, or event that
    aren't really about a distinct, individually-tracked person -- e.g. the
    Robe/Sash of the Theotokos, or Christ's Robe -- where inventing a solo
    Saint identity just to satisfy the FK would be worse than having none
    (see docs/saint-model-refactor.md, Stage 8)."""

    day = models.ForeignKey('calendarium.Day', on_delete=models.CASCADE)
    saint = models.ForeignKey(Saint, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=200, default='')
    story = models.TextField(null=True, blank=True)
    rank = models.SmallIntegerField(default=0)
    high_rank = models.BooleanField(default=False)
    new_style = models.BooleanField(default=False)
    day_native = models.BooleanField(default=True)
    ordering = models.SmallIntegerField(default=0)
    tradition = models.CharField(max_length=16, choices=[
        ('common', 'Common'),  # shared by all traditions (the default)
        ('slavic', 'Slavic-specific'),
        ('greek', 'Greek-specific'),
    ], default='common')

    class Meta:
        unique_together = 'day', 'saint'
        ordering = 'ordering',

    def __repr__(self):
        return f'<DayCommemoration: {self.title}>'

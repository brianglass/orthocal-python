import math

from datetime import date, datetime, timedelta, timezone
from enum import IntEnum, StrEnum

import jdcal

from dateutil.easter import easter

Weekday = IntEnum('Weekday', (
    'Sunday',
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
), start=0)

class Calendar(StrEnum):
    Gregorian = 'gregorian'
    Julian = 'julian'

class Tradition(StrEnum):
    Slavic = 'slavic'
    Greek = 'greek'

def cal_session_key(tradition):
    """The calendar preference is remembered per-tradition, since Greek is
    always Gregorian and shouldn't clobber a Slavic Julian/Gregorian choice."""
    return f'cal_{tradition}'

class Translation(StrEnum):
    KJV = 'kjv'
    LXX2012WEB = 'lxx2012-web'

def translation_session_key(language):
    """Mirrors cal_session_key(tradition): translation choice is remembered
    per-language, since it's only meaningful for English today."""
    return f'translation_{language}'

# Display labels for every translation code that can appear in Verse rows,
# not just the ones selectable via the dropdown -- rccv/srp1865 are included
# so the "Scripture Readings (...)" heading is accurate for Romanian/Serbian
# too, instead of always showing "(KJV)" regardless of language.
TRANSLATION_LABELS = {
    'kjv': 'King James Version',
    'lxx2012-web': 'LXX2012 & WEB',
    'rccv': 'Romanian Corrected Cornilescu Version',
    'srp1865': 'Serbian (Karadžić/Daničić, 1865)',
}

class FastLevels(IntEnum):
    NoFast         = 0
    Fast           = 1
    LentenFast     = 2
    ApostlesFast   = 3
    DormitionFast  = 4
    NativityFast   = 5

FastLevelDesc = (
    "No Fast",
    "Fast",
    "Lenten Fast",
    "Apostles Fast",
    "Dormition Fast",
    "Nativity Fast",
)

FastExceptions = (
    '',
    "Wine and Oil are Allowed",
    "Fish, Wine and Oil are Allowed",
    "Wine and Oil are Allowed",
    "Fish, Wine and Oil are Allowed",
    "Wine is Allowed",
    "Wine, Oil and Caviar are Allowed",
    "Meat Fast",
    "Strict Fast (Wine and Oil)",
    "Strict Fast",
    "No overrides",
    "Fast Free",
)

class DietaryAllowance(IntEnum):
    """A clean, monotonic (strict -> fully free) dietary ladder.

    FastExceptions above mixes real dietary rungs with app-internal
    bookkeeping values (indices 1/3 and 2/4 are textually identical -- the
    same rung reached via different weekday-adjustment code paths in
    Day._apply_fasting_adjustments -- and 0/10 are "no annotation"/"no
    overrides" sentinels rather than dietary rungs in their own right). This
    enum is the clean version: exactly one member per distinct dietary
    state, ordered by permissiveness.

    WineOilCaviar is the Lazarus Saturday caviar exception; dietarily it
    excludes the same categories as WineAndOil (caviar is an extra
    allowance callout, not an additional abstention).
    """

    Strict        = 0
    WineOnly      = 1
    WineAndOil    = 2
    WineOilCaviar = 3
    FishWineOil   = 4
    MeatFast      = 5
    FastFree      = 6

# The food categories abstained from at each rung, in a fixed
# most-to-least-restrictive display order. Inverse of the exclusion sets
# antiochian.org publishes in its own "ABSTAIN FROM ..." phrasing (see
# ingest_antiochian.py's DIETARY_ALLOWANCE_TO_FAST_EXCEPTION for the
# corresponding legacy fast_exception indices).
ABSTENTIONS_BY_RUNG = {
    DietaryAllowance.Strict:        ('meat', 'fish', 'dairy', 'eggs', 'wine', 'oil'),
    DietaryAllowance.WineOnly:      ('meat', 'fish', 'dairy', 'eggs', 'oil'),
    DietaryAllowance.WineAndOil:    ('meat', 'fish', 'dairy', 'eggs'),
    DietaryAllowance.WineOilCaviar: ('meat', 'fish', 'dairy', 'eggs'),
    DietaryAllowance.FishWineOil:   ('meat', 'dairy', 'eggs'),
    DietaryAllowance.MeatFast:      ('meat',),
    DietaryAllowance.FastFree:      (),
}

# Canonicalizes the legacy fast_exception index (0-11) onto one clean
# DietaryAllowance rung. Verified against every value actually present in
# the fixture data, not guessed: 0/9/10 all land on real strict-fast dates
# (ordinary Wed/Fri, Great and Holy Friday, Theophany/Nativity Eve, Clean
# Week/Holy Week); 8 ("Strict Fast (Wine and Oil)") lands on Beheading of
# John the Baptist and Exaltation of the Cross, which are dietarily
# identical to plain wine-and-oil (1/3), just labeled to flag that the day
# would otherwise default to something stricter.
FAST_EXCEPTION_TO_DIETARY_ALLOWANCE = {
    0:  DietaryAllowance.Strict,
    1:  DietaryAllowance.WineAndOil,
    2:  DietaryAllowance.FishWineOil,
    3:  DietaryAllowance.WineAndOil,
    4:  DietaryAllowance.FishWineOil,
    5:  DietaryAllowance.WineOnly,
    6:  DietaryAllowance.WineOilCaviar,
    7:  DietaryAllowance.MeatFast,
    8:  DietaryAllowance.WineAndOil,
    9:  DietaryAllowance.Strict,
    10: DietaryAllowance.Strict,
    11: DietaryAllowance.FastFree,
}

def fast_abstentions_for(fast_level, fast_exception):
    """Maps (fast_level, fast_exception) to the food categories abstained
    from, e.g. ['meat', 'fish', 'dairy', 'eggs'] -- the inverse of the
    traditional "what's allowed" framing (fast_exception_desc), for readers
    who don't already know what e.g. "Wine and Oil are Allowed" implies is
    forbidden.

    fast_level only distinguishes NoFast (nothing abstained) from every
    actual fasting day; the specific dietary state is otherwise fully
    determined by fast_exception alone, so there's no need to branch on
    fast_level beyond that one check.

    Reflects typikon-strict practice (e.g. plain, non-Lenten Wednesdays/
    Fridays resolve to the full Strict rung); many jurisdictions relax this
    pastorally, which this function does not attempt to model.
    """

    if fast_level == FastLevels.NoFast:
        return []

    rung = FAST_EXCEPTION_TO_DIETARY_ALLOWANCE[fast_exception]
    return list(ABSTENTIONS_BY_RUNG[rung])

FeastLevels = {
	-1: "No Liturgy",
	0:  "Liturgy",
	1:  "Presanctified",
	2:  "Black squigg (6-stich typikon symbol)",
	3:  "Red squigg (doxology typikon symbol)",
	4:  "Red cross (polyeleos typikon symbol)",
	5:  "Red cross half-circle (vigil typikon symbol)",
	6:  "Red cross circle (great feast typikon symbol)",
	7:  "Major feast Theotokos",
	8:  "Major feast Lord",
}

class FloatIndex(IntEnum):
    FathersSix                      = 1001   # Fathers of the first six ecumenical councils
    FathersSeventh                  = 1002   # Fathers of the seventh ecumenical council
    DemetriusSaturday               = 1003   # Demetrius Saturday
    SynaxisUnmercenaries            = 1004   # Synaxis of unmercenaries
    SatBeforeElevationMoved         = 1005   # Saturday before Elevation when moved to September 13
    SatBeforeElevation              = 1006   # Saturday before Elevation on Saturday
    SunBeforeElevation              = 1007   # Sunday before Elevation
    SatAfterElevation               = 1008   # Saturday after Elevation
    SunAfterElevation               = 1009   # Sunday after Elevation
    SunForefathers                  = 1010   # Sunday of Forefathers
    SatBeforeNativity               = 1011   # Saturday before Nativity standalone
    SunBeforeNativity               = 1012   # Sunday before Nativity standalone
    RoyalHoursNativityFriday        = 1013   # Royal Hours of Nativity when moved to Friday
    EveNativity                     = 1014   # Eve of Nativity standalone
    SatBeforeNativityEve            = 1015   # Saturday before Nativity == Eve
    SunBeforeNativityEve            = 1016   # Sunday before Nativity == Eve
    SatAfterNativityBeforeTheophany = 1017   # Saturday after Nativity == Saturday before Theophany
    SatAfterNativityFriday          = 1018   # Saturday after Nativity moved to Friday
    SatAfterNativity                = 1019   # Saturday after Nativity standalone
    SunAfterNativityMonday          = 1020   # Sunday after Nativity moved to Monday
    SunAfterNativitiy               = 1021   # Sunday after Nativity standalone
    SatBeforeTheophany              = 1022   # Saturday before Theophany standalone
    SatBeforeTheophanyJan           = 1023   # Saturday before Theophany moved to January 1
    SunBeforeTheophany              = 1024   # Sunday before Theophany standalone
    RoyalHoursTheophanyFriday       = 1025   # Royal Hours of Theophany when moved to Friday
    TheophanyEve                    = 1026   # Eve of Theophany standalone
    SatBeforeTheophanyEve           = 1027   # Saturday before Theophany == Eve
    SunBeforeTheophanyEve           = 1028   # Sunday before Theophany == Eve
    SatAfterTheophany               = 1029   # Saturday after Theophany
    SunAfterTheophany               = 1030   # Sunday after Theophany
    NewMartyrsRussia                = 1031   # New Martyrs of Russia
    AnnunciationParemFriday         = 1032   # Annunciation Paremias on Friday
    AnnunciationSat                 = 1033   # Annunciation on Saturday
    AnnunciationSun                 = 1034   # Annunciation on Sunday
    AnnunciationMon                 = 1035   # Annunciation on Monday
    AnnunciationParemEve            = 1036   # Annunciation Paremias on Eve
    AnnunciationWeekday             = 1037   # Annunciation on Tuesday-Friday
    LeavetakingTheophanyWeekday     = 1038   # Leavetaking of Theophany (theophany+8) on an ordinary weekday
    RaphaelBrooklyn                 = 1039   # First Saturday of November -- Greek-only, see docs/greek-fasting.md


def compute_pascha_jdn(year):
    """Compute the Julian day number of Pascha for the given year."""

    # See https://dateutil.readthedocs.io/en/stable/easter.html
    if not 1583 <= year <= 4099:
        raise ValueError(f'{year} is outside a valid year range for this application.')

    dt = easter(year, method=2)
    return gregorian_to_jdn(dt)

def weekday_from_pdist(distance):
    """Return the day of the week given the distance from Pascha."""
    return Weekday(distance % 7)

def surrounding_weekends(distance):
    weekday = weekday_from_pdist(distance)

    saturdaybefore = distance - weekday - 1
    sundaybefore = distance - 7 + ((7 - weekday) % 7)
    saturdayafter = distance + 7 - ((weekday + 1) % 7)
    sundayafter = distance + 7 - weekday

    return saturdaybefore, sundaybefore, saturdayafter, sundayafter

# conversion functions

def gregorian_to_julian(year, month, day):
    """Convert a Gregorian date to a Julian date."""

    if not 1583 <= year <= 4099:
        raise ValueError('The year is outside a valid range for this application.')

    jd = jdcal.gcal2jd(year, month, day)
    year, month, day, _ = jdcal.jd2jcal(*jd)

    # On a year that is a Julian Leap year but not a Gregorian leap year, this
    # will raise a ValueError. This is a problem, but doesn't occur until 2100.
    return date(year, month, day)

def compute_pascha_distance(dt):
    """Compute the distance of a given day from Pascha.

    Returns the distance and the year.  If the distance is < -77, the returned
    year will be earlier than the one passed in."""

    year = dt.year

    jdn = gregorian_to_jdn(dt)
    distance = jdn - compute_pascha_jdn(year)

    if distance < -77:
        year -= 1
        distance = jdn - compute_pascha_jdn(year)

    return distance, year

def compute_julian_pascha_distance(dt):
    """Compute the distance of a given day from Pascha.

    Returns the distance and the year.  If the distance is < -77, the returned year
    will be earlier than the one passed in."""

    year = dt.year

    jdn = julian_to_jdn(dt)
    distance = jdn - compute_pascha_jdn(dt.year)

    if distance < -77:
        year -= 1
        distance = jdn - compute_pascha_jdn(year)

    return distance, year

def julian_to_jdn(dt):
    """Convert a Julian date to a Julian day number."""

    jd = jdcal.jcal2jd(dt.year, dt.month, dt.day)
    jdn = math.ceil(sum(jd))
    return jdn

def gregorian_to_jdn(dt):
    """Convert a Gregorian date to a Julian day number.
    This function mimic's PHP's gregoriantojd()."""

    jd = jdcal.gcal2jd(dt.year, dt.month, dt.day)
    jdn = math.ceil(sum(jd))
    return jdn

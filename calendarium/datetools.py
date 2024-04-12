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

# Function to generate an ordinal number from an integer
def ordinal(n):
    # This was written by Github Copilot. I have no idea how it works.
    return "%d%s" % (n,"tsnrhtdd"[(math.floor(n/10)%10!=1)*(n%10<4)*n%10::4])

def get_day_name(pdist):
    weekday = weekday_from_pdist(pdist)
    if pdist > 50:
        # Generate the text "<weekday> of the <nth> week after Pentecost"
        nth = ordinal(abs(pdist-50) // 7 + 1)
        return f'{weekday.name} of the {nth} week after Pentecost'
    elif pdist > 0:
        nth = ordinal(abs(pdist) // 7 + 1)
        return f'{weekday.name} of the {nth} week of Pascha'
    elif pdist == 0:
        return 'Great and Holy Pascha'
    elif pdist < 0:
        nth = ordinal(abs(pdist) // 7 + 1)
        return f'{weekday.name} of the {nth} week before Pascha'

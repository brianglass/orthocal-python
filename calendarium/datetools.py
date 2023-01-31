import math

from datetime import date, datetime, timedelta, timezone
from enum import IntEnum

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

FastLevels = IntEnum('FastLevels', (
    'NoFast',
    'Fast',
    'LentenFast',
    'ApostlesFast',
    'DormitionFast',
    'NativityFast',
), start=0)

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


def compute_pascha_jdn(year):
    """Compute the Julian day number of Pascha for the given year."""

    # See https://dateutil.readthedocs.io/en/stable/easter.html
    assert 1583 <= year <= 4099, 'The year is outside a valid range for this application.'
    dt = easter(year, method=2)
    return gregorian_to_jdn(dt)

def weekday_from_pdist(distance):
    """Return the day of the week given the distance from Pascha."""
    return distance % 7

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

    assert 1583 <= year <= 4099, 'The year is outside a valid range for this application.'
    jd = jdcal.gcal2jd(year, month, day)
    year, month, day, _ = jdcal.jd2jcal(*jd)
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

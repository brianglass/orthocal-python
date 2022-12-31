from datetime import date, datetime, timedelta, timezone
from enum import IntEnum

Weekday = IntEnum('Weekday', 'Sunday Monday Tuesday Wednesday Thursday Friday Saturday', start=0)

def compute_julian_pascha(year):
    """Compute the Julian date of Pascha for the given year."""

    # Use the Meeus Julian algorithm to calculate the Julian date
    # See https://en.wikipedia.org/wiki/Computus#Meeus'_Julian_algorithm
    a = year % 4
    b = year % 7
    c = year % 19
    d = (19*c + 15) % 30
    e = (2*a + 4*b - d + 34) % 7
    month = (d + e + 114) // 31
    day = (d+e+114)%31 + 1

    return date(year, month, day)

def compute_pascha_jdn(year):
    """Compute the Julian day number of Pascha for the given year."""

    dt = compute_julian_pascha(year)
    return julian_to_jdn(dt)

def compute_gregorian_pascha(year):
    """Compute the Gregorian date of Pascha for the given year.
    The year must be between 2001 and 2099."""

    pascha = compute_julian_pascha(year)
    return julian_to_gregorian(pascha)

def compute_pascha_distance(year, month, day):
    """Compute the distance of a given day from Pascha.

    Returns the distance and the year.  If the distance is < -77, the returned
    year will be earlier than the one passed in."""

    jdn = gregorian_date_to_jdn(year, month, day)
    distance = jdn - compute_pascha_jdn(year)

    if distance < -77:
        year -= 1
        distance = jdn - compute_pascha_jdn(year)

    return distance, year

def compute_julian_pascha_distance(dt):
    """Compute the distance of a given day from Pascha.

    Returns the distance and the year.  If the distance is < -77, the returned
    year will be earlier than the one passed in."""

    jdn = julian_to_jdn(dt)
    distance = jdn - compute_pascha_jdn(year)

    if distance < -77:
        year -= 1
        distance = jdn - compute_pascha_jdn(year)

    return distance, year

def weekday_from_pdist(distance):
    """Return the day of the week given the distance from Pascha."""
    return (7 + distance%7) % 7

def surrounding_weekends(distance):
    weekday = weekday_from_pdist(distance)

    saturdaybefore = distance - weekday - 1
    sundaybefore = distance - 7 + ((7 - weekday) % 7)
    saturdayafter = distance + 7 - ((weekday + 1) % 7)
    sundayafter = distance + 7 - weekday

    return saturdaybefore, sundaybefore, saturdayafter, sundayafter

# conversion functions

def julian_to_gregorian(dt):
    """convert a julian date to a gregorian date."""

    # this function will be incorrect outside the range 2001-2099 for 2 reasons:
    #
    # 1. the offset of 13 is incorrect outside the range 1900-2099.
    # 2. if the julian date is in february and on a year that is divisible by
    #    100, the go time module will incorrectly add the offset because these years
    #    are leap years on the julian, but not on the gregorian.
    #
    # hopefully this code will no longer be running by 2100.

    assert 2001 <= dt.year <= 2099, 'The year must be between 2001 and 2099.'

    # add an offset of 13 to convert from julian to gregorian
    return dt + timedelta(days=13)

def gregorian_to_julian(year, month, day):
    """Convert a Gregorian date to a Julian date."""

    # This function will be incorrect outside the range 2001-2099 for 2 reasons:
    #
    # 1. The offset of 13 is incorrect outside the range 1900-2099.
    # 2. If the Julian date is in February and on a year that is divisible by
    #    100, the datetime module will incorrectly add the offset because these years
    #    are leap years on the Julian, but not on the Gregorian.
    #
    # Hopefully this code will no longer be running by 2100.

    assert 2001 <= year <= 2099, 'The year must be between 2001 and 2099.'

    # Add an offset of 13 to convert from Gregory to Julian
    gregorian_date = date(year=year, month=month, day=day)
    return gregorian_date - timedelta(days=13)

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

    year = dt.year
    month = dt.month
    day = dt.day

    # See https://en.wikipedia.org/wiki/Julian_day#Converting_Julian_calendar_date_to_Julian_Day_Number
    return 367*year - (7*(year+5001+int((month-9)/7)))//4 + (275*month)//9 + day + 1729777

def gregorian_to_jdn(dt):
    """Convert a Gregorian date to a Julian day number.
    This function mimic's PHP's gregoriantojd()."""

    year = dt.year
    month = dt.month
    day = dt.day

    if month > 2:
        month -= 3
    else:
        month += 9
        year -= 1

    # break up the year into the leftmost 2 digits (century) and the rightmost 2 digits
    century = year // 100
    ya = year - 100 * century

    return 146097*century//4 + 1461*ya//4 + (153*month+2)//5 + day + 1721119

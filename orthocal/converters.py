from django.urls.converters import IntConverter

from calendarium.datetools import Calendar

CAL_RE = '(gregorian|julian|oca|rocor)'

class CalendarConverter:
    regex = CAL_RE

    def to_python(self, value):
        if value in ('gregorian', 'oca'):
            return Calendar.Gregorian

        if value in ('julian', 'rocor'):
            return Calendar.Julian

    def to_url(self, value):
        return value


class YearConverter(IntConverter):
    def to_python(self, value):
        year = super().to_python(value)

        if not 1583 <= year <= 4099:
            raise ValueError('The year is outside a valid range for this application.')

        return year


class MonthConverter(IntConverter):
    def to_python(self, value):
        month = super().to_python(value)

        if not 1 <= month <= 12:
            raise ValueError('The month is outside a valid range.')

        return month


class DayConverter(IntConverter):
    def to_python(self, value):
        day = super().to_python(value)

        if not 1 <= day <= 31:
            raise ValueError('The day is outside a valid range.')

        return day

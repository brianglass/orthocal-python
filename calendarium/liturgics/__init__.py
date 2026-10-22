from datetime import datetime, timedelta

from .day import Day, SlavicDay, GreekDay
from .year import ByzantineYear, SlavicYear, GreekYear

def month_of_days(year, month, **kwargs):
    dt = datetime(year, month, 1)
    while dt.month == month:
        yield Day(dt.year, dt.month, dt.day, **kwargs)
        dt += timedelta(days=1)

from datetime import datetime, timedelta

from .day import Day
from .year import Year

async def amonth_of_days(year, month, use_julian=False):
    dt = datetime(year, month, 1)
    while dt.month == month:
        day = Day(dt.year, dt.month, dt.day, use_julian=use_julian)
        await day.ainitialize()
        yield day
        dt += timedelta(days=1)

def month_of_days(year, month, use_julian=False):
    dt = datetime(year, month, 1)
    while dt.month == month:
        day = Day(dt.year, dt.month, dt.day, use_julian=use_julian)
        day.initialize()
        yield day
        dt += timedelta(days=1)

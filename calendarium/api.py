from datetime import datetime, timedelta

from rest_framework import viewsets
from rest_framework.response import Response

from . import liturgics
from . import serializers


class DayViewSet(viewsets.ViewSet):
    def retrieve(self, request, year, month, day):
        day = liturgics.Day(year, month, day)
        day.initialize()
        serializer = serializers.DaySerializer(day)
        return Response(serializer.data)

    def list(self, request, year, month):
        days = self._get_days_in_month(year, month)
        serializer = serializers.DaySerializer(days, many=True, context={'exclude_passage': True})
        return Response(serializer.data)

    def _get_days_in_month(self, year, month):
        dt = datetime(year, month, 1)
        while dt.month == month:
            day = liturgics.Day(dt.year, dt.month, dt.day)
            day.initialize()
            yield day
            dt += timedelta(days=1)

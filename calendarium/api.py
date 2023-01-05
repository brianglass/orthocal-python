from datetime import datetime, timedelta

from rest_framework import viewsets
from rest_framework.response import Response

from . import liturgics
from . import serializers


class DayViewSet(viewsets.ViewSet):
    def retrieve(self, request, year, month, day, jurisdiction='oca'):
        if jurisdiction == 'oca':
            day = liturgics.Day(year, month, day)
        else:
            day = liturgics.Day(year, month, day, use_julian=True)

        day.initialize()
        serializer = serializers.DaySerializer(day)
        return Response(serializer.data)

    def list(self, request, year, month, jurisdiction='oca'):
        if jurisdiction == 'oca':
            days = liturgics.month_of_days(year, month)
        else:
            days = liturgics.month_of_days(year, month, use_julian=True)

        # Exclude the scriptures passages for the list view to keep the response times low.
        serializer = serializers.DaySerializer(days, many=True, context={'exclude_passage': True})
        return Response(serializer.data)

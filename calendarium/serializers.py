from asgiref.sync import async_to_sync
from rest_framework import serializers


class ListField(serializers.ListField):
    def to_representation(self, value):
        """Return None for an empty list to maintain backward compatibility
        with the Go version."""
        return super().to_internal_value(value) or None


class VerseSerializer(serializers.Serializer):
    book = serializers.CharField()
    chapter = serializers.IntegerField()
    verse = serializers.IntegerField()
    content = serializers.CharField()


class ReadingSerializer(serializers.Serializer):
    source = serializers.CharField()
    book = serializers.CharField()
    description = serializers.CharField(source='desc')
    display = serializers.CharField()
    short_display = serializers.CharField(source='sdisplay')
    passage = VerseSerializer(source='get_passage', many=True)

    def get_fields(self):
        fields = super().get_fields()

        if self.context.get('exclude_passage'):
            fields.pop('passage', None)

        return fields


class DaySerializer(serializers.Serializer):
    pascha_distance = serializers.IntegerField(source='pdist')
    julian_day_number = serializers.IntegerField(source='jdn')
    year = serializers.IntegerField()
    month = serializers.IntegerField()
    day = serializers.IntegerField()
    weekday = serializers.IntegerField()
    tone = serializers.IntegerField()

    titles = ListField(child=serializers.CharField())

    feast_level = serializers.IntegerField()
    feast_level_description = serializers.CharField(source='feast_level_desc')
    feasts = ListField(child=serializers.CharField())

    fast_level = serializers.IntegerField()
    fast_level_desc = serializers.CharField()
    fast_exception = serializers.IntegerField()
    fast_exception_desc = serializers.CharField()

    saints = ListField(child=serializers.CharField())
    service_notes = ListField(child=serializers.CharField())

    readings = serializers.SerializerMethodField()

    def get_readings(self, instance):
        readings = instance.get_readings()
        return ReadingSerializer(readings, many=True, context=self.context).data

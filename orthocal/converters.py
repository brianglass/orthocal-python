class CalendarConverter:
    regex = '(oca|rocor|gregorian|julian)'

    def to_python(self, value):
        if value == 'oca':
            return 'gregorian'
        elif value == 'rocor':
            return 'julian'
        else:
            return value

    def to_url(self, value):
        return value

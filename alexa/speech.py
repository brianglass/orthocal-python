import itertools
import math
import re

from django.utils import timezone

from calendarium.datetools import FastLevels

MAX_SPEECH_LENGTH = 8000

ref_re = re.compile('(\d*)\s*([\w\s]+)\s+(\d+)')
markup_re = re.compile('<.*?>')

EPISTLES = {
    "acts":          "The Acts of the Apostles",
    "romans":        "Saint Paul's letter to the Romans",
    "corinthians":   "Saint Paul's <say-as interpret-as=\"ordinal\">%s</say-as> letter to the Corinthians",
    "galatians":     "Saint Paul's letter to the Galatians",
    "ephesians":     "Saint Paul's letter to the Ephesians",
    "philippians":   "Saint Paul's letter to the Philippians",
    "colossians":    "Saint Paul's letter to the Colossians",
    "thessalonians": "Saint Paul's <say-as interpret-as=\"ordinal\">%s</say-as> letter to the Thessalonians",
    "timothy":       "Saint Paul's <say-as interpret-as=\"ordinal\">%s</say-as> letter to Timothy",
    "titus":         "Saint Paul's letter to Titus",
    "philemon":      "Saint Paul's letter to Philemon",
    "hebrews":       "Saint Paul's letter to the Hebrews",
    "james":         "The Catholic letter of Saint James",
    "peter":         "The <say-as interpret-as=\"ordinal\">%s</say-as> Catholic letter of Saint Peter",
    "john":          "The <say-as interpret-as=\"ordinal\">%s</say-as> Catholic letter of Saint John",
    "jude":          "The Catholic letter of Saint Jude",
}

SUBSTITUTIONS = (
    ('Ven.', '<sub alias="The Venerable">Ven.</sub>'),
    ('Ss', '<sub alias="Saints">Ss.</sub>'),
)

def day_speech(day):
    speech_text = ''
    card_text = ''

    # Titles

    when = when_speech(day)

    if day.titles:
        speech_text += f'<p>{when}, is the {day.titles[0]}.</p>'
        card_text += f'{when}, is the {day.titles[0]}\n\n'

    # Fasting

    speech_text += f'<p>{fasting_speech(day)}</p>'
    if day.fast_exception_desc:
        card_text += f'{day.fast_level_desc} \u2013 {day.fast_exception_desc}\n\n'
    else:
        card_text += f'{day.fast_level_desc}\n\n'

    # Feasts

    if len(day.feasts) > 1:
        feast_list = human_join(day.feasts)
        text = f'The feasts celebrated are: {feast_list}.'
        speech_text += f'<p>{text}</p>'
        card_text += f'{text}\n\n'
    elif len(day.feasts) == 1:
        text = f'The feast of {day.feasts[0]} is celebrated.'
        speech_text += f'<p>{text}</p>'
        card_text += f'{text}\n\n'

    # Commemorations

    if len(day.saints) > 1:
        text = f'The commemorations are for {human_join(day.saints)}.'
        speech_text += f'<p>{text}</p>'
        card_text += f'{text}\n\n'
    elif len(day.saints) == 1:
        text = f'The commemoration is for {day.saints[0]}.'
        speech_text += f'<p>{text}</p>'
        card_text += f'{text}\n\n'

    # Readings

    for reading in day.get_readings():
        card_text += f'{reading.display}\n'

    speech_text = expand_abbreviations(speech_text)
    return speech_text, card_text

def when_speech(day):
    today = timezone.localtime().date()
    delta = day.gregorian_date - today

    if 0 <= delta.days < 1:
        return 'Today, ' + day.gregorian_date.strftime("%B %-d")
    elif 1 <= delta.days < 2:
        return 'Tomorrow, ' + day.gregorian_date.strftime("%B %-d")
    else:
        return day.gregorian_date.strftime("%A, %B %-d")

def fasting_speech(day):
    match day.fast_level:
        case FastLevels.NoFast:
            return 'On this day there is no fast.'
        case FastLevels.Fast:
            # normal weekly fast
            if len(day.fast_exception_desc) > 0:
                return f'On this day there is a fast. {day.fast_exception_desc}.'
            else:
                return 'On this day there is a fast.'
        case FastLevels.LentenFast | FastLevels.ApostlesFast | FastLevels.DormitionFast | FastLevels.NativityFast:
            # One of the four great fasts
            if len(day.fast_exception_desc) > 0:
                return f'This day is during the {day.fast_level_desc}. {day.fast_exception_desc}.'
            else:
                return f'This day is during the {day.fast_level_desc}.'

def human_join(words):
    if len(words) > 1:
        return ', '.join(words[:-1]) + f' and {words[-1]}'
    else:
        return words[0]

def reading_speech(reading, end=None):
    reference = reference_speech(reading)
    reading_text = f'<p>The reading is from {reference}.</p> <break strength="medium" time="750ms"/>'

    passage = reading.get_passage()

    if passage.count() == 0:
        reading_text += '<p>Orthodox Daily could not find that reading.</p>'
        return reading_text

    for i, verse in enumerate(passage):
        if end and i >= end:
            break

        stripped = markup_re.sub('', verse.content)
        reading_text += f'<p>{stripped}</p>'

    return reading_text

def reading_range_speech(reading, start, end):
    reading_text = ''
    passage = reading.get_passage()

    for verse in passage[start:end]:
        stripped = markup_re.sub('', verse.content)
        reading_text += f'<p>{stripped}</p>'

    return reading_text

def reference_speech(reading):
    match = ref_re.search(reading.display)

    try:
        number, book, chapter = match.groups()
    except ValueError:
		# The reference is irregular so we just let Alexa do the best she can
        return read.display.replace('.', ':')

    match reading.book.lower():
        case 'matthew' | 'mark' | 'luke' | 'john':
            return f'The Holy Gospel according to Saint {book}, chapter {chapter}'
        case 'apostol':
            if epistle := EPISTLES.get(book.lower()):
                if number:
                    epistle = epistle % number

                return f'{epistle}, chapter {chapter}'
            else:
                return f'{book}, chapter {chapter}'
        case 'ot':
            if number:
                return f'<say-as interpret-as="ordinal">{number}</say-as> {book}, chapter {chapter}'
            else:
                return f'{book}, chapter {chapter}'
        case _:
            return reading.display.replace('.', ':')

def expand_abbreviations(speech_text):
    for abbr, full in SUBSTITUTIONS:
        speech_text = speech_text.replace(abbr, full)

    return speech_text

def get_passage_len(passage, start=None, end=None):
    markup_len = len('<p></p>')

    if start is None or end is None :
        return sum(len(p.content) + markup_len for p in passage)
    else:
        return sum(len(p.content) + markup_len for p in passage[start:end])

def estimate_group_size(passage):
    """Estimate how many verses need to be in each group."""

    # Use extreme examples for length guesses
    prelude = len("<p>There are 29 readings for Tuesday, January 3. The reading is from Saint Paul's <say-as interpret-as=\"ordinal\">2</say-as> letter to the Thessalonians</p>")
    postlude = len('<p>Would you like to hear the next reading?</p>')
    group_postlude = len('<p>This is a long reading. Would you like me to continue?</p>')

    verse_count = passage.count()

    passage_len = prelude + get_passage_len(passage) + postlude
    if passage_len < MAX_SPEECH_LENGTH:
        return None

    # Start with a good guess and then grow the group count until we find one
    # that fits.
    group_count = passage_len // MAX_SPEECH_LENGTH + 1

    while True:
        # estimate the number of verses per group
        group_size = math.ceil(verse_count / group_count)

        # Try building each group and fail if one is too big
        for g in range(group_count):
            start = g * group_size
            end = start + group_size
            length = get_passage_len(passage, start, end)

            if g == 0:
                length += prelude

            if g == group_count - 1:
                length += postlude
            else:
                length += group_postlude

            # If a group is too big, it's time to try a bigger group count
            if length > MAX_SPEECH_LENGTH:
                group_count += 1
                break
        else:
            return group_size

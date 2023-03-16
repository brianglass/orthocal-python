import itertools
import math
import re

from django.utils import timezone

from calendarium.datetools import FastLevels

MAX_SPEECH_LENGTH = 8000

ref_re = re.compile('(\d*)\s*([\w\s]+)\s+(\d+)')
ssml_re = re.compile(r'<(?!p\b)(.*?)>(.*?)</\1>')


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

ABBREVIATIONS = {
    # Keys should not have '.' in them. That is taken care of by the RE.
    # Keys should all be lowercase.
    'ven':      'The Venerable',
    'st':       'Saint',
    'ss':       'Saints',
    'sts':      'Saints',
    '~':        'Approximately',
    'ca':       'Circa',
    'transl':   'Translation',
    'trans':    'Translation',
    'rel':      'Relics',
    'c':        'Century',
    'metr':     'Metropolitan',
    'patr':     'Patriarch',
    'abp':      'Archbishop',
    'ch':       'Chapter',
}

PHONETICS = {
    # Use the International Phonetic Alphabet (IPA) for phonetics.
    # Keys should all be lowercase.
    'theotokos':    'θˈɛoʊtˈoʊkoʊs',
    'paschal':      'pæs.kəl',
    'pascha':       'pɑskə',
}

abbreviations_re = re.compile(
    r'(\b(' + '|'.join(ABBREVIATIONS.keys()) + r')\b\.?)'
    r'|\b(' + '|'.join(PHONETICS.keys()) + r')\b',
    flags=re.IGNORECASE
)

def expand_abbreviations(speech_text):
    def replace(match):
        full_abbr, abbr, phonetic = match.groups()
        if abbr:
            return f'<sub alias="{ABBREVIATIONS[abbr.lower()]}">{full_abbr}</sub>'
        else:
            return f'<phoneme alphabet="ipa" ph="{PHONETICS[phonetic.lower()]}">{phonetic}</phoneme>'

    return abbreviations_re.sub(replace, speech_text)

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

    for reading in day.get_abbreviated_readings():
        card_text += f'{reading.pericope.display}\n'

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
            if day.fast_exception_desc:
                return f'On this day there is a fast. {day.fast_exception_desc}.'
            else:
                return 'On this day there is a fast.'
        case FastLevels.LentenFast | FastLevels.ApostlesFast | FastLevels.DormitionFast | FastLevels.NativityFast:
            # One of the four great fasts
            if day.fast_exception_desc:
                return f'This day is during the {day.fast_level_desc}. {day.fast_exception_desc}.'
            else:
                return f'This day is during the {day.fast_level_desc}.'

def human_join(words):
    if len(words) > 1:
        return ', '.join(words[:-1]) + f' and {words[-1]}'
    else:
        return words[0]

def ssml_strip_markup(text):
    return ssml_re.sub(r'\2', text)

def reference_speech(reading):
    match = ref_re.search(reading.pericope.display)

    try:
        number, book, chapter = match.groups()
    except ValueError:
		# The reference is irregular so we just let Alexa do the best she can
        return read.display.replace('.', ':')

    match reading.pericope.book.lower():
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
            elif book == 'Composite':
                return f'{book} {chapter}'
            else:
                return f'{book}, chapter {chapter}'
        case _:
            return reading.pericope.display.replace('.', ':')

def reading_speech(reading, end=None):
    scripture_text = reading_range_speech(reading, end=end)

    if not scripture_text:
        return '<p>Orthodox Daily could not find that reading.</p>'

    reference = reference_speech(reading)

    return (
            f'<p>The reading is from {reference}.</p> '
            f'<break strength="medium" time="750ms"/> {scripture_text}'
    )

def reading_range_speech(reading, start=None, end=None):
    passage = reading.pericope.get_passage()
    return '\n'.join(f'<p>{verse.content}</p>' for verse in passage[start:end])

def estimate_group_size(passage):
    """Estimate how many verses need to be in each group."""

    # Use extreme examples for length guesses
    prelude_len = len('<p>There are 29 scripture readings for Tuesday, January 3. <break strength="strong" time="1500ms"/>The reading is from Saint Paul\'s <say-as interpret-as="ordinal">2</say-as> letter to the Thessalonians</p>')
    postlude_len = len('<p>Would you like to hear the next reading?</p>')
    prompt_len = len('<p>This is a long reading. Would you like me to continue?</p>')
    markup_len = len('<p></p>\n')

    verse_lengths = [len(p.content) + markup_len for p in passage]

    passage_len = prelude_len + sum(verse_lengths) + postlude_len
    if passage_len < MAX_SPEECH_LENGTH:
        return None

    # Start with a good guess and then grow the group count until we find one
    # that fits.
    group_count = math.ceil(passage_len / MAX_SPEECH_LENGTH)

    while True:
        # estimate the number of verses per group
        group_size = math.ceil(len(verse_lengths) / group_count)

        # Try building each group and fail if one is too big
        for g in range(group_count):
            start = g * group_size
            end = start + group_size
            length = sum(verse_lengths[start:end])

            if g == 0:
                length += prelude_len

            if g == group_count - 1:
                # The postlude is read after the last group of verses
                length += postlude_len
            else:
                # The prompt is read between groups of verses
                length += prompt_len

            # If a group is too big, it's time to try a bigger group count
            if length > MAX_SPEECH_LENGTH:
                group_count += 1
                break
        else:
            return group_size

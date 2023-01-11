from django.utils import timezone

from .datetools import FastLevels

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

def day_speech(builder, day):
    speech_text = ''

    when = when_speech(day)

    if day.titles:
        speech_text += f'<p>{when}, is the {day.titles[0]}.</p>'

    speech_text += f'<p>{fasting_speech(day)}</p>'

    # Feasts
    if len(day.feasts) > 1:
        feast_list = human_join(day.feasts)
        speech_text += f'<p>The feasts celebrated are: {feast_list}.</p>'
    elif len(day.feasts) == 1:
        speech_text += f'<p>The feast of {day.feasts[0]} is celebrated.</p>'

    # Commemorations
    if len(day.saints) > 1:
        speech_text += f'The commemorations are for {human_join(day.saints)}.'
    elif len(day.saints) == 1:
        speech_text += f'The commemoration is for {day.saints[0]}.'

    # TODO: make custom card text
    speech_text = speech_text.replace('Ven.', '<sub alias="The Venerable">Ven.</sub>')
    return speech_text, speech_text

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

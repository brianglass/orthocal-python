import logging

from datetime import datetime

from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import get_slot_value, is_request_type, is_intent_name
from ask_sdk_model.ui import SimpleCard
from django.template.loader import render_to_string
from django.utils import timezone

from . import liturgics
from . import speech

logger = logging.getLogger(__name__)
skill_builder = SkillBuilder()

# These handlers don't seem to support async

def get_day(handler_input):
    session_attributes = handler_input.attributes_manager.session_attributes

    if date_text := session_attributes.get('date'):
        try:
            dt = datetime.strptime(date_text, '%Y-%m-%d')
        except ValueError:
            return None
    elif date_text := get_slot_value(handler_input, 'date'):
        try:
            dt = datetime.strptime(date_text, '%Y-%m-%d')
        except ValueError:
            return None
    else:
        dt = timezone.localtime()

    day = liturgics.Day(dt.year, dt.month, dt.day)
    day.initialize()

    return day


class LaunchHandler(AbstractRequestHandler):
    """Handle intial launch of the skill.

    Give some basic information about today. Optionally continue on with
    scripture readings.
    """

    def can_handle(self, handler_input):
        return is_request_type('LaunchRequest')(handler_input)

    def handle(self, handler_input):
        builder = handler_input.response_builder
        session_attributes = handler_input.attributes_manager.session_attributes

        logger.debug('Running OrthodoxDailyLaunchHandler.')

        today = timezone.localtime()
        day = liturgics.Day(today.year, today.month, today.day)
        day.initialize()

        speech_text, card_text = speech.day_speech(day)

        # Set speech
        num_readings = len(day.get_readings())
        speech_text += (
                f'<p>There are {num_readings} scripture readings. '
                f'Would you like to hear the readings?</p>'
        )
        builder.speak(speech_text)

        # Set card
        card = SimpleCard('About Today', card_text)
        builder.set_card(card)

        # Prepare to read the scriptures if requested
        builder.set_should_end_session(False)
        session_attributes['original_intent'] = 'Launch'
        session_attributes['next_reading'] = 0
        session_attributes['date'] = timezone.localtime().strftime('%Y-%m-%d')

        return builder.response


class DayIntentHandler(AbstractRequestHandler):
    """Give some basic details about an explicitly requested day."""

    def can_handle(self, handler_input):
        return is_intent_name('Day')(handler_input)

    def handle(self, handler_input):
        builder = handler_input.response_builder

        logger.debug('Running DayIntentHander.')

        if not (day := get_day(handler_input)):
            builder.set_should_end_session(True)
            builder.speak("<p>I didn't understand the date you requested.</p>")
            return builder.response

        # Set speech
        speech_text, card_text = speech.day_speech(day)
        builder.speak(speech_text)

        # Set card
        when = speech.when_speech(day)
        card = SimpleCard(f'About {when}', card_text)
        builder.set_card(card)

        # there are no further steps in this interaction
        builder.set_should_end_session(True)

        return builder.response


class ScripturesIntentHandler(AbstractRequestHandler):
    """Build the initial scriptures Speech.

    We read the first reading on the initial Scriptures intent request and
    subsequent readings are triggered on AMAZON.YesIntent or
    AMAZON.NextIntent requests.
    """

    def can_handle(self, handler_input):
        return is_intent_name('Scriptures')(handler_input)

    def handle(self, handler_input):
        builder = handler_input.response_builder
        session_attributes = handler_input.attributes_manager.session_attributes

        logger.debug('Running ScripturesIntentHander.')

        if not (day := get_day(handler_input)):
            builder.set_should_end_session(True)
            builder.speak("<p>I didn't understand the date you requested.</p>")
            return builder.response

        readings = day.get_readings()

        # Build card

        date_text = day.gregorian_date.strftime('%A, %B %-d')
        card_text = f'Readings for {date_text}:\n\n'

        for reading in readings:
            card_text += f'{reading.display}\n'

        when = speech.when_speech(day)
        card = SimpleCard(f'About {when}', card_text)
        builder.set_card(card)

        # Build speech

        passage = readings[0].get_passage()
        group_size = speech.estimate_group_size(passage)

        date_text = day.gregorian_date.strftime('%A, %B %-d')

        if group_size is not None and group_size > 0:
            reading_speech = speech.reading_speech(readings[0], group_size)
        else:
            reading_speech = speech.reading_speech(readings[0])

        speech_text = (
                f'<p>There are {len(readings)} readings for {date_text}.</p> '
                '<break strength="strong" time="1500ms"/>'
                f'<p>{reading_speech}</p>'
        )

        # Prepare to handle the next step in the interaction

        session_attributes['original_intent'] = 'Scriptures'
        if group_size:
            # We continue with the first reading, since it's long
            builder.set_should_end_session(False)
            session_attributes['next_reading'] = 0
            session_attributes['next_verse'] = group_size
            session_attributes['group_size'] = group_size
            session_attributes['date'] = day.gregorian_date.strftime('%Y-%m-%d')
            speech_text += '<p>This is a long reading. Would you like me to continue?</p> '
        elif len(readings) > 1:
            # We move on the the 2nd reading
            builder.set_should_end_session(False)
            session_attributes['next_reading'] = 1
            session_attributes['date'] = day.gregorian_date.strftime('%Y-%m-%d')
            speech_text += '<p>Would you like to hear the next reading?</p> '
        else:
            # There was only one reading and we're done. This should never happen.
            builder.set_should_end_session(True)
            speech_text += '<p>That is the end of the readings.</p>'

        builder.speak(speech_text)

        return builder.response


class NextIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return (
                is_intent_name('AMAZON.YesIntent')(handler_input) or
                is_intent_name('AMAZON.NextIntent')(handler_input)
        )

    def _bail(self, handler_input, message):
        builder = handler_input.response_builder
        builder.set_should_end_session(True)
        builder.speak(message)
        return builder.response

    def handle(self, handler_input):
        builder = handler_input.response_builder
        session_attributes = handler_input.attributes_manager.session_attributes

        logger.debug('Running NextIntentHander.')

        # Check for the original intent. If none are valid, bail.
        original_intent = session_attributes.get('original_intent')
        if original_intent not in ('Launch', 'Scriptures'):
            return self._bail(handler_input, "<p>I'm not sure what you mean in this context.</p>")

        # Get the relevant day. If we can't figure out which day, bail.
        if not (day := get_day(handler_input)):
            return self._bail(handler_input, "<p>I didn't understand the date you requested.</p>")

        # Figure out which is the next reading. If we can't, bail.
        if (next_reading := session_attributes.get('next_reading')) is None:
            return self._bail(handler_input, "<p>I don't know what you mean in this context.</p>")

        readings = day.get_readings()

        # If we have already completed the final reading, let the user know and exit.
        if next_reading >= len(readings):
            return self._bail(handler_input, "<p>There are no more readings.</p>")

        reading = readings[next_reading]
        passage = reading.get_passage()

        # Is this a long passage?
        if group_size := session_attributes.get('group_size'):
            next_verse = session_attributes.get('next_verse', 0)
        else:
            group_size = speech.estimate_group_size(passage)
            next_verse = 0

        # Get the scripture reading as speech
        if next_verse > 0:
            speech_text = speech.reading_range_speech(reading, next_verse, next_verse + group_size)
        elif group_size is not None and group_size > 0:
            speech_text = speech.reading_speech(reading, group_size)
        else:
            speech_text = speech.reading_speech(reading)

        speech_text += '<break strength="medium" time="750ms"/>'

        # Update session attributes
        if group_size is not None and group_size > 0 and next_verse + group_size < passage.count():
            builder.set_should_end_session(False)
            session_attributes['next_verse'] = next_verse + group_size
            session_attributes['group_size'] = group_size
            speech_text += 'This is a long reading. Would you like me to continue?'
        elif next_reading + 1 >= len(readings):
            builder.set_should_end_session(True)
            speech_text += 'That is the end of the readings.'
        else:
            builder.set_should_end_session(False)
            session_attributes['next_reading'] = next_reading + 1
            session_attributes.pop('next_verse', None)
            session_attributes.pop('group_size', None)
            speech_text += 'Would you like to hear the next reading?'

        builder.speak(speech_text)

        return builder.response


class StopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return (
                is_intent_name('AMAZON.NoIntent')(handler_input) or
                is_intent_name('AMAZON.CancelIntent')(handler_input) or
                is_intent_name('AMAZON.StopIntent')(handler_input)
        )

    def handle(self, handler_input):
        builder = handler_input.response_builder
        builder.set_should_end_session(True)
        session_attributes.pop('date', None)
        session_attributes.pop('next_reading', None)
        session_attributes.pop('original_intent', None)
        return builder.response


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name('AMAZON.HelpIntent')(handler_input)

    def handle(self, handler_input):
        builder = handler_input.response_builder
        session_attributes = handler_input.attributes_manager.session_attributes

        speech_text = render_to_string('help.ssml')
        card_text = speech.markup_re.sub('', speech_text)

        builder.speak(speech_text)

        card = SimpleCard('Help', card_text)
        builder.set_card(card)

        builder.set_should_end_session(False)
        session_attributes.pop('date', None)
        session_attributes.pop('next_reading', None)
        session_attributes.pop('original_intent', None)

        return builder.response


skill_builder.add_request_handler(LaunchHandler())
skill_builder.add_request_handler(DayIntentHandler())
skill_builder.add_request_handler(ScripturesIntentHandler())
skill_builder.add_request_handler(NextIntentHandler())
skill_builder.add_request_handler(StopIntentHandler())
skill_builder.add_request_handler(HelpIntentHandler())

orthodox_daily_skill = skill_builder.create()

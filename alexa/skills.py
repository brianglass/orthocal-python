import logging
import re

from datetime import datetime

from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import get_slot_value, is_request_type, is_intent_name
from ask_sdk_model.ui import SimpleCard
from django.template.loader import render_to_string
from django.utils import timezone

from . import speech
from calendarium import liturgics

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
        session = handler_input.attributes_manager.session_attributes

        # Make sure we don't have any left over junk from a previous session.
        session.clear()

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

        # Prepare for the readings if requested.
        builder.set_should_end_session(False)
        session['date'] = today.strftime('%Y-%m-%d')
        session['task_queue'] = ['scriptures', 'commemorations']
        session['current_task'] = None

        return builder.response


class DayIntentHandler(AbstractRequestHandler):
    """Give some basic details about an explicitly requested day."""

    def can_handle(self, handler_input):
        return is_intent_name('Day')(handler_input)

    def handle(self, handler_input):
        builder = handler_input.response_builder
        session = handler_input.attributes_manager.session_attributes

        # Make sure we don't have any left over junk from a previous session.
        session.clear()

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
        session = handler_input.attributes_manager.session_attributes

        # Make sure we don't have any left over junk from a previous session.
        session.clear()

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
            card_text += f'{reading.pericope.display}\n'

        when = speech.when_speech(day)
        card = SimpleCard(f'About {when}', card_text)
        builder.set_card(card)

        # Build speech

        passage = readings[0].pericope.get_passage()
        group_size = speech.estimate_group_size(passage)
        date_text = day.gregorian_date.strftime('%A, %B %-d')
        reading_speech = speech.reading_speech(readings[0], group_size)

        speech_text = (
                f'<p>There are {len(readings)} scripture readings for {date_text}.</p> '
                '<break strength="strong" time="1500ms"/>'
                f'<p>{reading_speech}</p>'
        )

        # Prepare to handle the next step in the interaction

        session['task_queue'] = []
        session['current_task'] = 'scriptures'

        if group_size:
            # We continue with the first reading, since it's long
            builder.set_should_end_session(False)
            session['next_reading'] = 0
            session['next_verse'] = group_size
            session['group_size'] = group_size
            session['date'] = day.gregorian_date.strftime('%Y-%m-%d')
            speech_text += '<p>This is a long reading. Would you like me to continue?</p> '
        elif len(readings) > 1:
            # We move on the the 2nd reading
            builder.set_should_end_session(False)
            session['next_reading'] = 1
            session['date'] = day.gregorian_date.strftime('%Y-%m-%d')
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
        session = handler_input.attributes_manager.session_attributes

        logger.debug('Running NextIntentHander.')

        if not (current_task := session.get('current_task')):
            try:
                # Get the next task from the queue
                current_task = session['task_queue'].pop(0)
            except (KeyError, IndexError):
                # We're in a wierd state; bail.
                return self._bail(handler_input, "<p>I'm not sure what you mean in this context.</p>")

            # Initialize the new task
            session['current_task'] = current_task
            if current_task == 'scriptures':
                session['next_reading'] = 0
                session['next_verse'] = 0
            elif current_task == 'commemorations':
                session['next_commemoration'] = 0

        if current_task == 'scriptures':
            return self.scriptures_handler(session, builder)
        elif current_task == 'commemorations':
            return self.commemorations_handler(session, builder)

    def commemorations_handler(self, session, builder):
        dt = datetime.strptime(session['date'], '%Y-%m-%d')
        day = liturgics.Day(dt.year, dt.month, dt.day)
        day.initialize()

        next_commemoration = session.get('next_commemoration')

        story = day.stories[next_commemoration]
        story_text = re.sub(r'<it>(.*?)</it>', r'\1', story.story)
        story_text = speech.expand_abbreviations(story_text)
        next_commemoration += 1

        speech_text = (
                f'<p>The commemoration is for {story.title}.</p>'
                '<break strength="medium" time="750ms"/>'
                f'{story_text}'
                '<break strength="medium" time="750ms"/>'
        )

        if next_commemoration < len(day.stories):
            # There are more commemorations to be read.
            speech_text += 'Would you like to hear the next commemoration?'
            builder.set_should_end_session(False)
            session['next_commemoration'] = next_commemoration
        elif session['task_queue']:
            # We have another task to complete
            builder.set_should_end_session(False)
            session['current_task'] = None
            speech_text += f'Would you like me to read the {session["task_queue"][0]}?'
        else:
            # We have read all the commemorations.
            speech_text += 'That is the end of the commemorations.'
            builder.set_should_end_session(True)
            session.clear()

        builder.speak(speech_text)

        return builder.response

    def scriptures_handler(self, session, builder):
        dt = datetime.strptime(session['date'], '%Y-%m-%d')
        day = liturgics.Day(dt.year, dt.month, dt.day)
        day.initialize()
        readings = day.get_readings()

        next_reading = session.get('next_reading')

        reading = readings[next_reading]
        passage = reading.pericope.get_passage()

        # Is this a long passage?
        if group_size := session.get('group_size'):
            next_verse = session.get('next_verse', 0)
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
            # We are reading a group of verses from the current reading
            builder.set_should_end_session(False)
            session['next_verse'] = next_verse + group_size
            session['group_size'] = group_size
            speech_text += 'This is a long reading. Would you like me to continue?'
        elif next_reading + 1 >= len(readings):
            # We have finished all of the scripture readings
            if session['task_queue']:
                # We have another task to complete
                builder.set_should_end_session(False)
                session['current_task'] = None
                speech_text += f'Would you like me to read the {session["task_queue"][0]}?'
            else:
                # We are done
                builder.set_should_end_session(True)
                session.clear()
                speech_text += 'That is the end of the readings.'
        else:
            # We have finished a complete reading and prompt to go on to the
            # next reading.
            builder.set_should_end_session(False)
            session['next_reading'] = next_reading + 1
            session.pop('next_verse', None)
            session.pop('group_size', None)
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
        session = handler_input.attributes_manager.session_attributes
        builder.set_should_end_session(True)
        session.clear()
        return builder.response


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name('AMAZON.HelpIntent')(handler_input)

    def handle(self, handler_input):
        builder = handler_input.response_builder
        session = handler_input.attributes_manager.session_attributes

        speech_text = render_to_string('help.ssml')
        card_text = speech.markup_re.sub('', speech_text)

        builder.speak(speech_text)

        card = SimpleCard('Help', card_text)
        builder.set_card(card)

        builder.set_should_end_session(False)

        return builder.response


skill_builder.add_request_handler(LaunchHandler())
skill_builder.add_request_handler(DayIntentHandler())
skill_builder.add_request_handler(ScripturesIntentHandler())
skill_builder.add_request_handler(NextIntentHandler())
skill_builder.add_request_handler(StopIntentHandler())
skill_builder.add_request_handler(HelpIntentHandler())

orthodox_daily_skill = skill_builder.create()

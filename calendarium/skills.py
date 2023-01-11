import logging

from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_model.ui import SimpleCard
from django.utils import timezone

from . import liturgics
from . import speech

logger = logging.getLogger(__name__)
skill_builder = SkillBuilder()

# These handlers don't seem to support async


class OrthodoxDailyLaunchHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type('LaunchRequest')(handler_input)

    def handle(self, handler_input):
        builder = handler_input.response_builder

        today = timezone.localtime()
        day = liturgics.Day(today.year, today.month, today.day)
        day.initialize()

        speech_text, card_text = speech.day_speech(day)
        builder.speak(speech_text)

        card = SimpleCard('About Today', card_text)
        builder.set_card(card)

        return builder.response


class DayIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name('Day')(handler_input)

    def handle(self, handler_input):
        builder = handler_input.response_builder
        attributes = handler_input.attributes_manager.request_attributes

        logger.debug(dir(attributes))
        if date_text := attributes.get('date'):
            date = datetime.strptime('%Y-%m-%d', date_text)
            day = liturgics.Day(date.year, date.month, date.day)
        else:
            today = timezone.localtime()
            day = liturgics.Day(today.year, today.month, today.day)

        day.initialize()

        speech_text, card_text = speech.day_speech(day)
        builder.speak(speech_text)

        when = speech.when_speech(day)
        card = SimpleCard(f'About {when}', card_text)
        builder.set_card(card)

        return builder.response


skill_builder.add_request_handler(OrthodoxDailyLaunchHandler())
skill_builder.add_request_handler(DayIntentHandler())

orthodox_daily_skill = skill_builder.create()

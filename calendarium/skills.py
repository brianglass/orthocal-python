from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_model.ui import SimpleCard
from django.utils import timezone

from . import liturgics
from . import speech

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

        speech, card_text = speech.day_speech(builder, day)
        builder.speak(speech)

        card = SimpleCard('About Today', card_text)
        builder.set_card(card)

        return builder.response


skill_builder.add_request_handler(OrthodoxDailyLaunchHandler())

orthodox_daily_skill = skill_builder.create()

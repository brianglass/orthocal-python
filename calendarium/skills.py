from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name

skill_builder = SkillBuilder()


class OrthodoxDailyLaunchHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type('LaunchRequest')(handler_input)

    def handle(self, handler_input):
        speech = 'This is a test.'
        handler_input.response_builder.speak(speech).set_card(speech)
        return handler_input.response_builder.response


skill_builder.add_request_handler(OrthodoxDailyLaunchHandler())

orthodox_daily_skill = skill_builder.create()

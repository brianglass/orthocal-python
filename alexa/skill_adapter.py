# django-ask-sdk breaks after ask-sdk-webservice-support 1.3.2. 
# This is a workaround.
# See https://github.com/alexa/alexa-skills-kit-sdk-for-python/issues/202
from django_ask_sdk import skill_adapter

skill_adapter.SIGNATURE_KEY = "HTTP_SIGNATURE_256"

from django_ask_sdk.skill_adapter import *

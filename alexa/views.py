#from django.shortcuts import render
from django_ask_sdk import skill_adapter

from .skills import orthodox_daily_skill

# See https://github.com/alexa/alexa-skills-kit-sdk-for-python/issues/202
# Note: creating the RequestVerifier instance here also allows it to persist
# between requests and saves an extra request to Amazon S3 to fetch a
# certificate for most requests.

request_verifier = skill_adapter.RequestVerifier(
    signature_cert_chain_url_key=skill_adapter.SIGNATURE_CERT_CHAIN_URL_KEY,
    signature_key='HTTP_SIGNATURE_256',
)

orthodox_daily_view = skill_adapter.SkillAdapter.as_view(
    skill=orthodox_daily_skill,
    verify_signature=False,
    verifiers=[request_verifier],
)

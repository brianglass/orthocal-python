# orthocal-python
Orthocal Rewritten in Python

## For Docker Development

Build image:

	docker-compose build

Run the image in a container locally. Local file changes will be automatically detected while running:

	docker-compose up local

Run the image locally as it will be run in production:

	docker-compose up web

Run tests:

	docker-compose run tests

## Local Configuration

You can create a local_settings.py file in the orthocal directory and add
custom Django settings. This file will be imported into the main settings.py file.

## Environment Variables:

These environment variables should be set in the runtime environment.
For orthocal.info, these are set in Google Cloud Run service. They can
also be passed to a container at runtime using the docker -e argument.
(See the Makefile for an example).

	SECRET_KEY - the Django secret key
	TZ - a valid timezone; the default is America/Los_angeles
	BASE_URL - the part of the url common to all urls on the site; the default is https://orthocal.info
	PORT - the port for the web service to listen on; This must be set. There is no default.
	ALLOWED_HOSTS - See Django docs for [ALLOWED_HOSTS](https://docs.djangoproject.com/en/4.2/ref/settings/#allowed-hosts).
	WEB_CONCURRENCY - How many processes to run (see uvicorn docs)

## For Local Development

Install dependencies:

	pip install -r requirements.txt

Load initial data:

	./manage.py collectstatic --noinput
	./manage.py migrate
	./manage.py loaddata calendarium commemorations

Run developement server:

	./manage.py runserver

Run tests:

	./manage.py test --keepdb

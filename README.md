# orthocal-python
Orthocal Rewritten in Python

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

## For Docker Development

Build image:

	make docker

Run the image in a container locally:

	make run

Run tests:

	make test

Push image to Google Container Registry (gcr.io):

	make deploy

## Environment Variables:

These environment variables should be set in the runtime environment.
For orthocal.info, these are set in Google Cloud Run service. They can
also be passed to a container at runtime using the docker -e argument.
(See the Makefile for an example).

	SECRET_KEY - the Django secret key
	TZ - a valid timezone; the default is America/Los_angeles
	BASE_URL - the part of the url common to all urls on the site; the default is https://orthocal.info
	PORT - the port for the web service to listen on; This must be set. There is no default.

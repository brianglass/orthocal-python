# For timings use the following:
# | ts -s '[%Y-%m-%d %H:%M:%.S]'
#
docker:
	docker build -t orthocal .

run:
	docker run -it -e PORT=8000 -e ALLOWED_HOST='localhost' -e WEB_CONCURRENCY=2 -p8000:8000 orthocal

uvicorn:
	# newrelic-admin run-program uvicorn --lifespan off --host 0.0.0.0 --port 8000 orthocal.asgi:application
	newrelic-admin run-program uvicorn --reload --lifespan off --host 0.0.0.0 --port 8000 orthocal.asgi:application
	# newrelic-admin run-program uvicorn --workers 2 --lifespan off --host 0.0.0.0 --port 8000 orthocal.asgi:application

deploy:
	docker tag orthocal:latest gcr.io/orthocal-1d1b9/orthocal:latest
	docker push gcr.io/orthocal-1d1b9/orthocal:latest

test:
	docker run -it -e PORT=8000 -p8000:8000 orthocal ./manage.py test

firebase:
	firebase use --add orthocal-1d1b9
	firebase deploy --only hosting

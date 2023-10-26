docker:
	docker build -t orthocal .

run:
	docker run -it -e PORT=8000 -e ALLOWED_HOST='localhost' -p8000:8000 orthocal

uvicorn:
	uvicorn --reload --lifespan off --host 0.0.0.0 --port 8000 orthocal.asgi:application
	#uvicorn --workers 3 --host 0.0.0.0 --port 8000 orthocal.asgi:application

deploy:
	docker tag orthocal:latest gcr.io/orthocal-1d1b9/orthocal:latest
	docker push gcr.io/orthocal-1d1b9/orthocal:latest

test:
	docker run -it -e PORT=8000 -p8000:8000 orthocal ./manage.py test

firebase:
	firebase use --add orthocal-1d1b9
	firebase deploy --only hosting

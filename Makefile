docker:
	docker build -t orthocal .

run:
	docker run -it -e PORT=8000 -p8000:8000 orthocal

deploy:
	docker tag orthocal:latest gcr.io/orthocal-1d1b9/orthocal:latest
	docker push gcr.io/orthocal-1d1b9/orthocal:latest

test:
	docker run -it -e PORT=8000 -p8000:8000 orthocal ./manage.py test

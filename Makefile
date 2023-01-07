docker:
	docker build -t orthocal .

run:
	docker run -it -p8000:8000 orthocal

deploy: docker
	docker tag orthocal:latest gcr.io/orthocal-1d1b9/orthocal:latest
	docker push gcr.io/orthocal-1d1b9/orthocal:latest

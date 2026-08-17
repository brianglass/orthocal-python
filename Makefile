# For timings use the following:
# | ts -s '[%Y-%m-%d %H:%M:%.S]'
#
docker:
	docker build -t orthocal .

run:
	docker run -it -e PORT=8000 -e ALLOWED_HOSTS='localhost' -e WEB_CONCURRENCY=4 -p8000:8000 orthocal

uvicorn:
	# newrelic-admin run-program uvicorn --lifespan off --host 0.0.0.0 --port 8000 orthocal.asgi:application
	newrelic-admin run-program uvicorn --lifespan off --host 0.0.0.0 --port 8000 --workers 4 orthocal.asgi:application
	# newrelic-admin run-program uvicorn --workers 2 --lifespan off --host 0.0.0.0 --port 8000 orthocal.asgi:application

deploy:
	docker tag orthocal:latest gcr.io/orthocal-1d1b9/orthocal:latest
	docker push gcr.io/orthocal-1d1b9/orthocal:latest

test:
	docker run -it -e PORT=8000 -p8000:8000 orthocal ./manage.py test

firebase: collectstatic
	firebase use --add orthocal-1d1b9
	firebase deploy --only hosting

# Regenerates static/ (Django's STATIC_ROOT) via the same collectstatic
# step the Dockerfile runs at image-build time, then mirrors it into
# public/media -- matching STATIC_URL='media/' -- so Firebase Hosting
# serves these files directly from its own CDN instead of proxying every
# request through Cloud Run. Firebase's rewrite in firebase.json only
# applies as a fallback for paths that don't match a real file under
# public/, so no rewrite changes are needed for this to take effect.
collectstatic:
	docker compose run --rm local ./manage.py collectstatic --noinput
	rm -rf public/media
	mkdir -p public/media
	cp -r static/* public/media/
	# servestatic pre-compresses sidecar files (.br/.gz/.zstd) for its own
	# on-disk serving scheme; Firebase Hosting compresses on the fly at its
	# own CDN edge and never looks for these, so they'd just be dead weight
	# in the deploy.
	find public/media \( -name '*.br' -o -name '*.gz' -o -name '*.zstd' \) -print0 | xargs -0 rm -f

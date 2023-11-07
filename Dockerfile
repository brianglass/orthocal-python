# This has to be pinned to Bullseye until oscrypto is updated
# See https://github.com/wbond/oscrypto/issues/78
FROM python:3.12-slim-bullseye

WORKDIR /orthocal

# newrelic.ini should be stored in Google Cloud Secret Manager and mounted as a volume.
ENV NEW_RELIC_CONFIG_FILE=/orthocal-secrets/newrelic.ini
CMD exec newrelic-admin run-program \
		 uvicorn --lifespan off --host 0.0.0.0 --port $PORT orthocal.asgi:application

# enables pip to install from git repos
RUN apt-get update && apt-get install -y git

COPY requirements.txt .
RUN pip install --upgrade pip && \
	pip install --no-cache-dir -r requirements.txt
COPY . .

# Precompile to bytecode to reduce warmup time
RUN \
	python -c "import compileall; compileall.compile_path(maxlevels=10)" && \
	python -m compileall .

# The sqlite database is read-only, so we build it into the image.
RUN \
	./manage.py collectstatic --noinput && \
	./manage.py migrate && \ 
	./manage.py loaddata calendarium commemorations

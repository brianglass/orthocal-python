FROM python:3.11-slim

WORKDIR /orthocal

# newrelic.ini should be stored in Google Cloud Secret Manager and mounted as a volume.
ENV NEW_RELIC_CONFIG_FILE=/orthocal-secrets/newrelic.ini
CMD exec newrelic-admin run-program \
		 uvicorn --host 0.0.0.0 --port $PORT --workers 2 orthocal.asgi:application

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
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

FROM python:3.12-slim

WORKDIR /orthocal

# newrelic.ini should be stored in Google Cloud Secret Manager and mounted as a volume.
# NEW_RELIC_CONFIG_FILE and NEW_RELIC_ENVIRONMENT should be set in GC Run as well.
# WEB_CONCURRENCY can also be set to specify the number of workers to run.
# The PORT environment variable is set by GC Run and controls the port server listens on.
CMD ["newrelic-admin", "run-program", "python", "server.py"]

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

FROM python:3.15-slim

WORKDIR /orthocal

# newrelic.ini should be stored in Google Cloud Secret Manager and mounted as a volume.
# NEW_RELIC_CONFIG_FILE and NEW_RELIC_ENVIRONMENT should be set in GC Run as well.
# WEB_CONCURRENCY can also be set to specify the number of workers to run.
# The PORT environment variable is set by GC Run and controls the port server listens on.
CMD ["newrelic-admin", "run-program", "python", "server.py"]

COPY requirements.txt .
# newrelic has no wheel for this Python, so pip builds it from source, and the
# slim image has no C compiler. Skip its optional C extensions outright:
# newrelic 14.0.0's fallback for a failed extension build is broken (its
# setup.py raises NameError on DistutilsPlatformError), and it would fall back
# to pure Python anyway.
ENV NEW_RELIC_EXTENSIONS=false
# --no-compile skips pip's own bytecode compilation during install -- the
# explicit compileall pass below (needed regardless, since it also covers
# our own app code, not just installed packages) makes it redundant.
# Uninstalling pip afterward drops ~14MB nothing at runtime needs -- the
# app never pip-installs anything itself.
RUN pip install --upgrade pip && \
	pip install --no-cache-dir --no-compile -r requirements.txt && \
	pip uninstall -y pip
COPY . .

# Precompile to bytecode to reduce warmup time
RUN \
	python -c "import compileall; compileall.compile_path(maxlevels=10)" && \
	python -m compileall .

# The sqlite database is read-only, so we build it into the image.
RUN \
	./manage.py collectstatic --noinput && \
	./manage.py migrate && \
	./manage.py loaddata calendarium commemorations && \
	./manage.py backfill_saint_slugs && \
	./manage.py backfill_saint_normalized_names && \
	./manage.py build_saint_search_index

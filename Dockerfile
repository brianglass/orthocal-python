FROM python:3.11-slim

WORKDIR /orthocal
CMD exec uvicorn --host 0.0.0.0 --port $PORT --workers 2 orthocal.asgi:application

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Precompile to bytecode to reduce warmup time
RUN \
	python -c "import compileall; compileall.compile_path(maxlevels=10)" && \
	python -m compileall .

RUN \
	./manage.py collectstatic --noinput && \
	./manage.py migrate && \ 
	./manage.py loaddata calendarium commemorations

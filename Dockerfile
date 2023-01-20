FROM python:3.11-slim

WORKDIR /orthocal

RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Precompile to bytecode to reduce warmup time
RUN python -c "import compileall; compileall.compile_path(maxlevels=10)"  # All installed packages
RUN python -m compileall .

RUN ./manage.py collectstatic --noinput
RUN ./manage.py migrate
RUN ./manage.py loaddata calendarium
RUN ./manage.py loaddata commemorations

CMD exec uvicorn --host 0.0.0.0 --port $PORT --workers 2 orthocal.asgi:application

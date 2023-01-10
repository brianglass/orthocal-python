FROM python:3.11-slim

RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN ./manage.py collectstatic --noinput
RUN ./manage.py migrate
RUN ./manage.py loaddata calendarium/fixtures/*

EXPOSE 8000
CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8000", "orthocal.asgi:application"]

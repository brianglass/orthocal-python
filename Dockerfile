FROM python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

EXPOSE 8000
ENTRYPOINT daphne orthocal.asgi:application -b 0.0.0.0 -p 8000

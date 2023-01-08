FROM python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN ./manage.py collectstatic --noinput

EXPOSE 8000
CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8000", "orthocal.asgi:application"]

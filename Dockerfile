FROM python:3.10

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code/app

COPY requirements.txt /code/app

RUN pip install -r /code/app/requirements.txt

RUN pip install --upgrade boto3
RUN pip install --upgrade psycopg2
RUN pip install --upgrade gunicorn
RUN pip install --upgrade django-crispy-forms
RUN pip install --upgrade celery
RUN pip install --upgrade django-celery-results

COPY . /code/app





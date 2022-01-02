FROM python:3.10

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code

COPY requirements.txt /code/

RUN pip install -r /code/requirements.txt

COPY . /code/
COPY /tmp/secrets/.env /code/The6ix/The6ix/



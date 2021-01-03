FROM python:3.9-slim-buster

RUN adduser --disabled-login --gecos "" bible

WORKDIR /home/bible/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    # i think gcc is included
    # i have no idea if build-essential, python3.9-dev or python3.9-venv are included
    apt-get install -y vlc && \
    apt-get autoremove

COPY . .

RUN make install

USER bible

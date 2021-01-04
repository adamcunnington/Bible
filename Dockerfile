FROM python:3.9-slim-buster

RUN adduser --disabled-login --gecos "" bible

WORKDIR /home/bible/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PULSE_SERVER=tcp:host.docker.internal:4713

RUN apt-get update && \
    apt-get install -y build-essential make pulseaudio vlc && \
    apt-get autoremove

COPY . .

RUN make install

USER bible

CMD make run-local

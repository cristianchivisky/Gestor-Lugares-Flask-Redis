FROM python:latest

WORKDIR /api

RUN pip3 install flask redis Flask-Bootstrap

expose 5000
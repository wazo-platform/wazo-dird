FROM python:3.9-slim-bullseye AS compile-image
LABEL maintainer="Wazo Maintainers <dev@wazo.community>"

RUN pip install flask

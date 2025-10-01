FROM python:3.11-slim-bookworm AS compile-image
LABEL maintainer="Wazo Maintainers <dev@wazo.community>"

RUN pip install flask

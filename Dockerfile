FROM python:3.11-slim-bookworm AS compile-image
LABEL maintainer="Wazo Maintainers <dev@wazo.community>"

RUN python3 -m venv /opt/venv
# Activate virtual env
ENV PATH="/opt/venv/bin:$PATH"

RUN apt-get -q update
RUN apt-get -yq install gcc libldap2-dev libsasl2-dev

COPY . /usr/src/wazo-dird
WORKDIR /usr/src/wazo-dird
RUN pip3 install -r requirements.txt
RUN python3 setup.py install

FROM python:3.11-slim-bookworm AS build-image
COPY --from=compile-image /opt/venv /opt/venv

COPY ./etc/wazo-dird /etc/wazo-dird
RUN true \
    && apt-get -q update \
    && apt-get -yq install libldap-2.5-0 \
    && mkdir -p /etc/wazo-dird/conf.d \
    && mkdir -p /etc/wazo-dird/templates.d \
    && install -o www-data -g www-data /dev/null /var/log/wazo-dird.log

EXPOSE 9489

# Activate virtual env
ENV PATH="/opt/venv/bin:$PATH"
CMD ["wazo-dird", "-d"]

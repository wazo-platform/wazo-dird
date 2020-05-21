FROM python:3.7-slim-buster AS compile-image
LABEL maintainer="Wazo Maintainers <dev@wazo.community>"

RUN python -m venv /opt/venv
# Activate virtual env
ENV PATH="/opt/venv/bin:$PATH"

RUN apt-get -q update
RUN apt-get -yq install gcc libldap2-dev libsasl2-dev

COPY . /usr/src/wazo-dird
WORKDIR /usr/src/wazo-dird
RUN pip install -r requirements.txt
RUN python setup.py install

FROM python:3.7-slim-buster AS build-image
COPY --from=compile-image /opt/venv /opt/venv

COPY ./etc/wazo-dird /etc/wazo-dird
RUN true \
    && mkdir -p /etc/wazo-dird/conf.d \
    && mkdir -p /etc/wazo-dird/templates.d \
    && install -o www-data -g www-data /dev/null /var/log/wazo-dird.log \
    && install -d -o www-data -g www-data /run/wazo-dird/

EXPOSE 9489

# Activate virtual env
ENV PATH="/opt/venv/bin:$PATH"
CMD ["wazo-dird", "-d"]

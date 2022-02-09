FROM wazoplatform/wazo-base-db
MAINTAINER Wazo Maintainers <dev@wazo.community>

ADD . /usr/src/wazo-dird
WORKDIR /usr/src/wazo-dird

RUN true \
    && pg_start \
    && bin/wazo-dird-init-db --user postgres \
    && (cd /usr/src/wazo-dird && alembic -c alembic.ini upgrade head) \
    && pg_stop \
    && true
USER postgres
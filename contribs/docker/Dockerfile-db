FROM wazoplatform/wazo-base-db
LABEL maintainer="Wazo Maintainers <dev@wazo.community>"

COPY . /usr/src/wazo-dird
WORKDIR /usr/src/wazo-dird
ENV ALEMBIC_DB_URI=postgresql://wazo-dird:Secr7t@localhost/wazo-dird

RUN true \
    && python3 setup.py install \
    && pg_start \
    && su postgres -c "psql -c \"CREATE ROLE \\"'"'"wazo-dird\\"'"'" LOGIN PASSWORD 'Secr7t';\"" \
    && su postgres -c "psql -c 'CREATE DATABASE \"wazo-dird\" WITH OWNER \"wazo-dird\";'" \
    && su postgres -c "psql \"wazo-dird\" -c 'CREATE EXTENSION \"uuid-ossp\";'" \
    && su postgres -c "psql \"wazo-dird\" -c 'CREATE EXTENSION \"unaccent\";'" \
    && su postgres -c "psql \"wazo-dird\" -c 'CREATE EXTENSION \"hstore\";'" \
    && (cd /usr/src/wazo-dird && python3 -m alembic.config -c alembic.ini upgrade head) \
    && pg_stop \
    && true
USER postgres

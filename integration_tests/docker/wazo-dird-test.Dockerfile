FROM wazoplatform/wazo-dird

ENV PYTHONDONTWRITEBYTECODE='true'

COPY . /usr/src/wazo-dird

WORKDIR /usr/src/wazo-dird
RUN python3 -m pip install -e . \
    && rm -f /etc/wazo-dird/conf.d/050-xivo-*.yml

WORKDIR /usr/src/wazo-dird/integration_tests/docker/broken-plugins
RUN python3 -m pip install -e .

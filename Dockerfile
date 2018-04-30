FROM python:2.7.13-stretch

ADD . /usr/src/wazo-dird
ADD ./contribs/docker/certs /usr/share/xivo-certs

WORKDIR /usr/src/wazo-dird

RUN apt-get -yq update \
   && apt-get -yqq install libldap2-dev libsasl2-dev \
   && mkdir -p /etc/xivo-dird/conf.d \
   && mkdir -p /etc/xivo-dird/templates.d \
   && mkdir -p /var/run/wazo-dird \
   && chmod a+w /var/run/wazo-dird \
   && touch /var/log/wazo-dird.log \
   && chown www-data: /var/log/wazo-dird.log \
   && pip install -r requirements.txt \
   && cp -r etc/* /etc \
   && python setup.py install \
   && apt-get -yqq remove libldap2-dev libsasl2-dev \
   && apt-get -yqq autoremove \
   && apt-get -yqq clean \
   && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ONBUILD ADD ./contribs/docker/certs /usr/share/xivo-certs

EXPOSE 9489

CMD ["wazo-dird", "-fd"]

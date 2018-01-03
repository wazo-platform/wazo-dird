FROM python:2.7.13

ADD . /usr/src/xivo-dird
ADD ./contribs/docker/certs /usr/share/xivo-certs

WORKDIR /usr/src/xivo-dird

RUN apt-get -yq update \
   && apt-get -yqq install libldap2-dev libsasl2-dev \
   && mkdir -p /etc/xivo-dird/conf.d \
   && mkdir -p /etc/xivo-dird/templates.d \
   && mkdir -p /var/run/xivo-dird \
   && chmod a+w /var/run/xivo-dird \
   && touch /var/log/xivo-dird.log \
   && chown www-data: /var/log/xivo-dird.log \
   && pip install -r requirements.txt \
   && cp -r etc/* /etc \
   && python setup.py install \
   && apt-get -yqq remove libldap2-dev libsasl2-dev \
   && apt-get -yqq autoremove \
   && apt-get -yqq clean \
   && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ONBUILD ADD ./contribs/docker/certs /usr/share/xivo-certs

EXPOSE 9489

CMD ["xivo-dird", "-fd"]

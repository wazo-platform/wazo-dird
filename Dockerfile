FROM python:2.7.9

RUN apt-get -yq update \
   && apt-get -yqq dist-upgrade \
   && apt-get -yqq install libldap2-dev libsasl2-dev \
   && apt-get -yq autoremove

RUN mkdir -p /etc/xivo-dird/conf.d

RUN mkdir -p /var/run/xivo-dird
RUN chmod a+w /var/run/xivo-dird

RUN touch /var/log/xivo-dird.log
RUN chown www-data: /var/log/xivo-dird.log

ADD . /usr/src/xivo-dird
ADD ./contribs/docker/certs /usr/share/xivo-certs
WORKDIR /usr/src/xivo-dird
RUN pip install -r requirements.txt
RUN cp -r etc/* /etc

RUN python setup.py install

ONBUILD ADD ./contribs/docker/certs /usr/share/xivo-certs

EXPOSE 9489

CMD ["xivo-dird", "-fd"]

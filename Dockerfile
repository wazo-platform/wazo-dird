FROM debian:latest

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get -qq update
RUN apt-get -qq -y install apt-utils
RUN apt-get -qq -y install \
     build-essential \
     python \
     python-pip \
     git \
     libpq-dev \
     libldap2-dev \
     libsasl2-dev \
     python-dev

RUN mkdir -p /etc/xivo-dird/conf.d

RUN mkdir -p /var/run/xivo-dird
RUN chmod a+w /var/run/xivo-dird

RUN touch /var/log/xivo-dird.log
RUN chown www-data: /var/log/xivo-dird.log

ADD . /usr/src/xivo-dird
ADD ./contribs/docker/certs /usr/share/xivo-certs
WORKDIR /usr/src/xivo-dird
RUN cp contribs/docker/listen.yml /etc/xivo-dird/conf.d/
RUN pip install -r requirements.txt
RUN rsync -av etc/ /etc

RUN python setup.py install

ONBUILD ADD ./contribs/docker/certs /usr/share/xivo-certs

EXPOSE 9489

CMD xivo-dird -d -f

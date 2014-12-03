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
     python-dev \
     nginx

ADD . /root/dird
RUN mkdir -p /var/run/xivo-dird
RUN chmod a+w /var/run/xivo-dird
RUN touch /var/log/xivo-dird.log
RUN chown www-data: /var/log/xivo-dird.log

WORKDIR /root/dird
RUN cp run.sh /root/run.sh
RUN pip install -r requirements.txt
RUN rsync -av etc/ /etc
RUN ln -s /etc/nginx/sites-available/xivo-dird /etc/nginx/sites-enabled/xivo-dird
RUN sed -i 's#127.0.0.1#0.0.0.0#' /etc/nginx/sites-available/xivo-dird

RUN python setup.py install
WORKDIR /root
RUN rm -fr /root/dird

EXPOSE 9489

CMD /root/run.sh

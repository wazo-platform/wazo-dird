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

ADD start start
RUN cp start /root
RUN chmod +x /root/start
RUN mkdir -p /var/run/xivo-dird
RUN chmod a+w /var/run/xivo-dird
RUN touch /var/log/xivo-dird.log
RUN chown www-data: /var/log/xivo-dird.log

WORKDIR /root
RUN git clone "git://github.com/xivo-pbx/xivo-dird"
WORKDIR xivo-dird
RUN git checkout dird-daemon
RUN pip install -r requirements.txt
RUN rsync -av etc/nginx/ /etc/nginx
RUN ln -s /etc/nginx/sites-available/xivo-dird /etc/nginx/sites-enabled/xivo-dird
RUN sed -i 's#/var/run/xivo-dird#/tmp#' /etc/nginx/sites-available/xivo-dird
RUN sed -i 's#127.0.0.1#0.0.0.0#' /etc/nginx/sites-available/xivo-dird

# to be removed after the merge
RUN pip install pyaml stevedore futures

RUN python setup.py install
WORKDIR /root
RUN rm -fr /root/xivo-dird

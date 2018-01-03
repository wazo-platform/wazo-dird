FROM debian:stretch

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get -qq update
RUN apt-get -qq -y install wget apt-utils

# Add xivo mirror
RUN echo "deb http://mirror.wazo.community/debian/ phoenix main" >> /etc/apt/sources.list
RUN wget http://mirror.wazo.community/wazo_current.key -O - | apt-key add -
RUN apt-get -qq update

# install xivo-dird
RUN apt-get -qq -y install xivo-dird

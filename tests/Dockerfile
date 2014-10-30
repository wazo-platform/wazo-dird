FROM xivo/dird_base:latest

ADD . /dird
WORKDIR /dird
RUN python setup.py install

EXPOSE 9489

CMD /root/start

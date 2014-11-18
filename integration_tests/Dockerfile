FROM xivo/dird_base:latest

ADD ./_context /dird
WORKDIR /dird
RUN python setup.py install

EXPOSE 9489

CMD /root/start

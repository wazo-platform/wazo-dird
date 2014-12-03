FROM xivo/dird

ADD ./_context /dird
WORKDIR /dird
RUN python setup.py install

EXPOSE 9489

CMD /root/run.sh

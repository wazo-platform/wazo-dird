FROM xivo/dird:latest

ADD ./_context /dird
WORKDIR /dird
RUN python setup.py install

EXPOSE 9489

CMD xivo-dird -d -f

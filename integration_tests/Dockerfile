FROM xivo/dird:latest

ADD ./_context /dird
WORKDIR /dird
RUN pip install -r requirements.txt
RUN python setup.py install

EXPOSE 9489

CMD xivo-dird -d -f

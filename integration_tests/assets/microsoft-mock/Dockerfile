FROM python:3.7-buster

COPY . /usr/src/microsoft-mock
WORKDIR /usr/src/microsoft-mock

RUN pip install -r requirements.txt

ENTRYPOINT [ "python" ]

EXPOSE 80

CMD [ "main.py" ]

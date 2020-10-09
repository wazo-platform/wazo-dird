# wazo-dird

[![Build Status](https://jenkins.wazo.community/buildStatus/icon?job=wazo-dird)](https://jenkins.wazo.community/job/wazo-dird)

wazo-dird is a service to query many directory sources simultaneously using a
simple REST API.

## Docker

The wazoplatform/wazo-dird image can be built using the following command:

```sh
docker build -t wazoplatform/wazo-dird .
```

The `wazoplatform/wazo-dird` image contains a configuration file to listen to HTTP
requests on "0.0.0.0". To change this behavior, create or edit the file
`/etc/wazo-dird/conf.d/listen.yml`

The wazoplatform/wazo-dird-db image can be built using the following command:

```sh
docker build -f contribs/docker/Dockerfile-db -t wazoplatform/wazo-dird-db .
```

## Running unit tests

```sh
apt-get install libpq-dev python-dev libffi-dev libyaml-dev libldap2-dev libsasl2-dev
pip install tox
tox --recreate -e py37
```

## Running integration tests

You need Docker installed.

```sh
cd integration_tests
pip install -U -r test-requirements.txt
make test-setup
make test
```

For developers, when adding/removing a plugin:

```sh
make egg-info
```

## Adding a new database migration

To add a new migration script for the database use the following command:

```sh
alembic -c alembic.ini revision -m "<description of the revision>"
```

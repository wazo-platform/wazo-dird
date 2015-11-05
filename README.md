# xivo-dird
[![Build Status](https://travis-ci.org/xivo-pbx/xivo-dird.png?branch=master)](https://travis-ci.org/xivo-pbx/xivo-dird)

xivo-dird is a service to query many directory sources simultaneously using a
simple REST API.


## Translations

To extract new translations:

    % python setup.py extract_messages

To create new translation catalog:

    % python setup.py init_catalog -l <locale>

To update existing translations catalog:

    % python setup.py update_catalog

Edit file `xivo_dird/translations/<locale>/LC_MESSAGES/messages.po` and compile
using:

    % python setup.py compile_catalog


## Docker

The xivo/xivo-dird image can be built using the following command:

    % docker build -t xivo/xivo-dird .

The `xivo/xivo-dird` image contains a configuration file to listen to HTTP
requests on "0.0.0.0". To change this behavior, create or edit the file
`/etc/xivo-dird/conf.d/listen.yml`


## Testing

xivo-dird contains unittests and integration tests

### unittests

Dependencies to run the unittests are in the `requirements.txt` file.

    % pip install -r requirements.txt -r test-requirements.txt

To run the unittests

    % nosetests xivo_dird

### Integration tests

You need:

    - docker
    % pip install -r integration_tests/test-requirements.txt

A docker image named `dird-test` is required to execute the test suite.
To build this image execute:

    % cd integration_tests
    % make test-setup

`make test-setup` downloads a bunch of Docker images so it takes a long time,
but it only needs to be run when dependencies of xivo-dird change in any way
(new Python library, new server connection, etc.)

To execute the integration tests execute:

    % make test

For developers, when adding/removing a plugin:

    % make egg-info

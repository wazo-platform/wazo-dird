xivo-dird
=========
[![Build Status](https://travis-ci.org/xivo-pbx/xivo-dird.png?branch=master)](https://travis-ci.org/xivo-pbx/xivo-dird)

xivo-dird is a service to query many directory sources simultaneously using a
simple REST API.


## Docker

The xivo/dird image can be built using the following command:

   % docker build -t xivo/dird .

You will need a configuration file that changes the listen address to 0.0.0.0.


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
    % pip install -r test-requirements.txt

A docker image named `dird-test` is required to execute the test suite.
To build this image execute:

    % cd integration_tests
    % make test-setup
    % make test-image

There are two steps in preparing the integration tests:

    - `make test-setup`: time consuming, but only needs to be run when
      dependencies of xivo-dird change in any way.
    - `make test-image`: a lot faster, and needs to be run when the code of
      xivo-dird changes.

To execute the integration tests execute:

    % nosetests integration_tests

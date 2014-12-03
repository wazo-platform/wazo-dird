xivo-dird
=========
[![Build Status](https://travis-ci.org/xivo-pbx/xivo-dird.png?branch=master)](https://travis-ci.org/xivo-pbx/xivo-dird)

xivo-dird is a service to query many directory sources simultaneously using a
simple REST API.


## Docker

The xivo/dird image can be build using the following command:

   % docker build -t xivo/dird .


## Testing

xivo-dird contains unittests and integration tests

### unittests

Dependencies to run the unittests are in the `requirements.txt` file.

    % pip -r requirements.txt

To run the unittests

    % nosetests xivo_dird

### Integration tests

docker is required to execute integration tests as well as the content of `test_requirements.txt`

    % pip install -r test-requirements.txt

A docker image named `dird-test` is required to execute the test suite.
To build this image execute:

    % cd integration_tests
    % make test-setup
    % make test-image

The `make test-setup` step is time consuming and should rarelly be required. It
pulls the required images that are going to be used for the dird-test image
that is built from the local source using `make test-image`.

To execute the integration tests execute:

    % nosetests integration_tests

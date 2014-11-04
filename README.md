xivo-dird
=========
[![Build Status](https://travis-ci.org/xivo-pbx/xivo-dird.png?branch=master)](https://travis-ci.org/xivo-pbx/xivo-dird)

xivo-dird is a library for accessing remote directories in XiVO


## Testing

xivo-dird contains unittests and integration tests

### unittests

Dependencies to run the unittests are in the `requirements.txt` file.

    % pip -r requirements.txt

To run the unittests

    % nosetests xivo_dird

### Integration tests

docker is required to execute integration tests as well as the content of `test_requirements.txt`

    % pip install -r test_requirements.txt

A docker image named `dird-test` is required to execute the test suite.
To build this image execute:

    % make test-setup
    % make test-image

The `make test-setup` step is time consuming and should rarelly be required. It creates a base image that is going to be used as the base for dird-test image that is build from the local source using `make test-image`.

To execute the integration tests execute:

    % nosetests tests

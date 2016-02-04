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


Running unit tests
------------------

```
apt-get install libpq-dev python-dev libffi-dev libyaml-dev libldap2-dev libsasl2-dev
pip install tox
tox --recreate -e py27
```


Running integration tests
-------------------------

You need Docker installed.

```
cd integration_tests
pip install -U -r test-requirements.txt
make test-setup
make test
```

For developers, when adding/removing a plugin:

    % make egg-info


### Generate .tx/config

    % tx set --auto-local -r xivo.xivo-dird 'xivo_dird/translations/<lang>/LC_MESSAGES/messages.po' --source-lang en --type PO --source-file xivo_dird/messages.pot --execute

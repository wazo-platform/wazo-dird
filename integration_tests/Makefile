.PHONY: test-setup build-dird build-db-image egg-info test microsoft-mock pull-images

microsoft-mock:
	docker build --no-cache -t microsoft-mock -f assets/microsoft-mock/Dockerfile assets/microsoft-mock

test-setup: egg-info pull-images build-dird build-db-image microsoft-mock

pull-images:
	docker pull alpine
	docker pull nickstenning/slapd
	docker pull p0bailey/docker-flask
	docker pull python:2.7.16-buster
	docker pull python:3.7-buster
	docker pull rabbitmq
	docker pull wazopbx/wait
	docker pull wazopbx/wazo-auth-mock
	# TODO(sileht:) wait for https://github.com/jamesdbloom/mockserver/pull/662 to be released
	#docker pull jamesdbloom/mockserver:mockserver-5.2.3
	docker pull sileht/mockserver


build-dird:
	docker build -t wazopbx/wazo-dird ..
	docker build --no-cache -t wazo-dird-test -f docker/Dockerfile-dird-test ..

build-db-image:
	docker build -f ../contribs/docker/Dockerfile-db -t wazopbx/wazo-dird-db ..

egg-info:
	cd .. && python setup.py egg_info
	cd docker/broken-plugins && python setup.py egg_info

test:
	pytest

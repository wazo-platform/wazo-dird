.PHONY: test-setup build-dird build-db-image egg-info test

test-setup: egg-info build-dird build-db-image
	docker pull alpine
	docker pull python:2.7
	docker pull p0bailey/docker-flask
	docker pull nickstenning/slapd
	docker pull n3llyb0y/wait
	docker pull rabbitmq

build-dird:
	docker build -t xivo/xivo-dird ..
	docker build --no-cache -t xivo-dird-test -f docker/Dockerfile-dird-test ..

build-db-image:
	docker build -f ../contribs/docker/Dockerfile-db -t xivo/xivo-dird-db ..

egg-info:
	cd .. && python setup.py egg_info
	cd docker/broken-plugins && python setup.py egg_info

test:
	nosetests

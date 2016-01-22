.PHONY: test-setup build-dird egg-info test

test-setup: egg-info build-dird
	docker pull python:2.7
	docker pull p0bailey/docker-flask
	docker pull nickstenning/slapd
	docker pull n3llyb0y/wait

build-dird:
	docker build -t xivo/xivo-dird ..
	docker build --no-cache -t xivo-dird-test -f docker/Dockerfile-dird-test ..

egg-info:
	cd .. && python setup.py egg_info
	cd docker/broken-plugins && python setup.py egg_info

test:
	nosetests

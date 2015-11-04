.PHONY: test-setup clean sync-context

test-setup: egg-info
	docker pull python:2.7
	docker pull p0bailey/docker-flask
	docker pull nickstenning/slapd
	docker pull n3llyb0y/wait
	docker build -t xivo/xivo-dird ..
	docker build -t xivo-auth-mock -f docker/Dockerfile-auth-mock ..
	docker build --no-cache -t xivo-dird-test -f docker/Dockerfile-dird-test ..

egg-info:
	cd .. && python setup.py egg_info
	cd docker/broken-plugins && python setup.py egg_info

test:
	nosetests

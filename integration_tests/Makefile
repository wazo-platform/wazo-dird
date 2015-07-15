.PHONY: test-setup clean sync-context

test-setup: egg-info
	docker pull python:2.7
	docker pull nickstenning/flask
	docker pull nickstenning/slapd
	docker pull n3llyb0y/wait
	docker build -t xivo/xivo-dird ..
	docker build -t xivo-auth-mock -f Dockerfile-auth-mock ..
	docker build --no-cache -t xivo-dird-test -f Dockerfile-dird-test ..

egg-info:
	cd .. && python setup.py install_egg_info

test:
	nosetests

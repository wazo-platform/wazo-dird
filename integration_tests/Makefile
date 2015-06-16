.PHONY: test-image test-setup clean sync-context

test-setup:
	docker build -t xivo/xivo-dird ..
	docker pull python:2.7
	docker pull nickstenning/flask
	docker pull nickstenning/slapd
	docker pull n3llyb0y/wait

test-image:
	docker build --no-cache -t xivo-dird-test -f Dockerfile ..

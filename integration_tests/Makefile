test-setup: egg-info build-dird build-db-image

build-dird:
	docker build -t wazoplatform/wazo-dird ..
	docker build --no-cache -t wazo-dird-test -f docker/Dockerfile-dird-test ..

build-db-image:
	docker build -f ../contribs/docker/Dockerfile-db -t wazoplatform/wazo-dird-db ..

egg-info:
	cd .. && python setup.py egg_info
	cd docker/broken-plugins && python setup.py egg_info

test:
	pytest

.PHONY: test-setup build-dird build-db-image egg-info test

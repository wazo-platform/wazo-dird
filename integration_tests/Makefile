microsoft-mock:
	docker build --no-cache -t microsoft-mock -f assets/microsoft-mock/Dockerfile assets/microsoft-mock

test-setup: egg-info build-dird build-db-image microsoft-mock

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

.PHONY: test-setup build-dird build-db-image egg-info test microsoft-mock

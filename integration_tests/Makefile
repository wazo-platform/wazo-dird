test-setup: egg-info build-dird build-db-image build-ws-mock-image

build-dird:
	docker build -t wazoplatform/wazo-dird ..
	docker build --no-cache -t wazo-dird-test -f docker/wazo-dird-test.Dockerfile ..

build-db-image:
	docker build --pull -f ../contribs/docker/wazo-dird-db.Dockerfile -t wazoplatform/wazo-dird-db:local ..

build-ws-mock-image:
	docker build -f docker/wazo-dird-ws-mock.Dockerfile -t wazoplatform/wazo-dird-ws-mock:local .

egg-info:
	cd .. && python setup.py egg_info
	cd docker/broken-plugins && python setup.py egg_info

test:
	pytest

.PHONY: test-setup build-dird build-db-image egg-info test

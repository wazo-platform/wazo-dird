.PHONY: test-image test-setup test-csv test

test:
	nosetests tests/suite

test-setup:
	docker build -t xivo/dird_base contribs/docker/base_test_image

test-image:
	ln -f tests/Dockerfile .
	docker build -t dird-test .
	rm -f Dockerfile

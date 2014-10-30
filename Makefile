.PHONY: test-image test-setup test-csv test

test:
	nosetests tests/suite

test-setup:
	docker build -t xivo/dird_base contribs/docker/base_test_image

test-image:
	ln -f tests/Dockerfile .
	docker build -t dird-test .
	rm -f Dockerfile

test-csv:
	docker run \
	-v /home/pcm/d/xivo-dird/tests/assets/test_csv_backend:/etc/xivo/xivo-dird \
	-p 9489:9489 -d dird-test

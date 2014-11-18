.PHONY: test-image test-setup clean sync-context

sync-context:
	rsync -av \
	--exclude '.git' \
	--exclude 'debian' \
	--exclude 'integration_tests' \
	--exclude 'contribs' \
	--exclude '*.pyc' \
	--exclude 'README.md' \
	--exclude 'LICENSE' \
	--exclude 'test_requirements.txt' \
	../ ./_context/

test-setup: sync-context
	docker pull python:2.7
	mv Dockerfile_base_image Dockerfile
	docker build -t xivo/dird_base .
	mv Dockerfile Dockerfile_base_image

test-image: sync-context
	mv Dockerfile_test_image Dockerfile
	docker build -t dird-test .
	mv Dockerfile Dockerfile_test_image

clean:
	rm -fr _context

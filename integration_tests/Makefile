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
	cp Dockerfile_base_image Dockerfile
	docker build -t xivo/dird_test_base .
	rm Dockerfile -fr

test-image: sync-context
	cp Dockerfile_test_image Dockerfile
	docker build --no-cache -t dird-test .
	rm Dockerfile -fr

clean:
	rm -fr _context

.PHONY: test-image test-setup clean

test-setup:
	docker build -t xivo/dird_base ../contribs/docker/base_test_image

test-image:
	rsync -av \
	--exclude '.git' \
	--exclude 'debian' \
	--exclude 'integration_tests' \
	--exclude 'contribs' \
	--exclude '*.pyc' \
	--exclude 'README.md' \
	--exclude 'etc' \
	--exclude 'LICENSE' \
	--exclude 'test_requirements.txt' \
	--exclude 'requirements.txt' \
	../ ./_context/
	mv Dockerfile_test_image Dockerfile
	docker build -t dird-test .
	mv Dockerfile Dockerfile_test_image

clean:
	rm -fr _context

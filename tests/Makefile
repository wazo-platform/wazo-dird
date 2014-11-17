.PHONY: test-image test-setup clean

test-setup:
	docker build -t xivo/dird_base ../contribs/docker/base_test_image

test-image:
	rsync -av \
	--exclude '.git' \
	--exclude 'debian' \
	--exclude 'tests' \
	--exclude 'contribs' \
	--exclude '*.pyc' \
	--exclude 'README.md' \
	--exclude 'etc' \
	--exclude 'LICENSE' \
	--exclude 'test_requirements.txt' \
	--exclude 'requirements.txt' \
	../ ./_context/
	docker build -t dird-test .

clean:
	rm -fr _context

.PHONY: test-image test-setup clean sync-context

# sync-context:
# 	rsync -av \
# 	--exclude '.git' \
# 	--exclude 'debian' \
# 	--exclude 'integration_tests' \
# 	--exclude 'contribs' \
# 	--exclude '*.pyc' \
# 	--exclude 'README.md' \
# 	--exclude 'LICENSE' \
# 	--exclude 'test_requirements.txt' \
# 	../ ./_context/

test-setup:
	docker build -t xivo/xivo-dird ..
	docker pull python:2.7
	docker pull nickstenning/slapd
	docker pull n3llyb0y/wait

test-image:
	docker build --no-cache -t xivo-dird-test -f Dockerfile ..

# clean:
# 	rm -fr _context

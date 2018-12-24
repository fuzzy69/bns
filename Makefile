DIR_PATH = $(shell pwd)
DIR_NAME = $(shell basename $$PWD)
DIR_TMP = /mnt/ramdisk/

help:
	@echo "clean - remove Python file artifacts"
	@echo "lint  - check style with flake8"
	@echo "tests - run unittests"
	@echo "setup - setup application"

setup:
	virtualenv -p python3 env
	. env/bin/activate && pip install -r requirements.txt

clean:
	find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rfv
	# find logs/ results/ | grep -E "(\.jpg|\.log|\.json)" | xargs -d '\n' rm -rfv

clean_all:
	find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rfv
	find logs/ results/ | grep -E "(\.jpg|\.log|\.json)" | xargs -d '\n' rm -rfv
	rm -r $(DIR_PATH)/data/mongo/*
	rm -r $(DIR_PATH)/data/mongo2/*
	rm -r $(DIR_PATH)/data/mongo3/*

unittest:
	python -m unittest discover -v

lint:
	flake8 --exclude .git,__pycache__,env,_ > _/lint.log

pack:
	rsync -arv --exclude-from '$(DIR_PATH)/_/rsync-exclude.txt' $(DIR_PATH) /mnt/ramdisk/
	cd $(DIR_TMP) && zip -r $(DIR_NAME).zip $(DIR_NAME)/*

copy:
	rsync -arv --exclude-from '$(DIR_PATH)/_/rsync-exclude.txt' $(DIR_PATH) /mnt/ramdisk/
	zip -r $(DIR_TMP)$(DIR_NAME).zip $(DIR_TMP)$(DIR_NAME)

docker_clean:
	docker stop $$(docker ps -a -q)
	docker rm $$(docker ps -a -q)

docker_build:
	# docker build -t "bns" .
	docker-compose build

docker_run:
	# docker run -p 5000:5000 bns
	docker-compose up

experiment:
	rsync -arv --exclude-from '$(DIR_PATH)/_/rsync-exclude-2.txt' $(DIR_PATH) /mnt/ramdisk/

pip_upgrade:
	pip install --upgrade pip

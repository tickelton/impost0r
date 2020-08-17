.PHONY: test help

all: help

help:
	@echo "available targets:"
	@echo "help        :    print this help message"
	@echo "run         :    run impost0r in pipenv"
	@echo "pylint      :    run pylint"
	@echo "test        :    run all unit tests"
	@echo "test_online :    run online unit tests"
	@echo "test_misc   :    run misc unit tests"
	@echo "requirements:    create requirements.txt"

run:
	pipenv run python3 impost0r.py

requirements:
	pipenv run pip freeze > requirements.txt

pylint:
	pipenv run pylint impost0r.py

test:
	pipenv run python -m unittest discover -v

test_online:
	pipenv run python -m unittest test.test_impost0r.Impost0rOnlineTests

test_misc:
	pipenv run python -m unittest test.test_impost0r.Impost0rMiscTests

cx_freeze:
	pipenv run cxfreeze --target-dir=dist impost0r.py


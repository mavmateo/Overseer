PYTHONPATH := shared/python

.PHONY: test-contracts check-python lint-structure

test-contracts:
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest discover -s tests/contracts

check-python:
	python3 -m compileall shared/python services tests

lint-structure:
	find . -maxdepth 2 -type d | sort


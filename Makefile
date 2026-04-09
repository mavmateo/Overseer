PYTHONPATH := shared/python

.PHONY: test-contracts test-ingestor test check-python lint-structure

test-contracts:
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest discover -s tests/contracts

test-ingestor:
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest discover -s tests/ingestor

test: test-contracts test-ingestor

check-python:
	python3 -m compileall shared/python services tests

lint-structure:
	find . -maxdepth 2 -type d | sort

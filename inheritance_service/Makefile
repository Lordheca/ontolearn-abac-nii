.PHONY: run test lint install-git-hooks

run:
	uvicorn main:app --host 0.0.0.0 --port 5000 --reload

test:
	ENVIRONMENT=test pytest

lint:
	pre-commit run --all-files

install-git-hooks:
	pre-commit install --hook-type pre-commit
	pre-commit install --hook-type commit-msg

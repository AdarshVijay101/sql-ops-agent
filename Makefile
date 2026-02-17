.PHONY: run test eval lint clean

run:
	docker compose up --build

test:
	pytest

eval:
	python sql_ops_agent/eval/harness.py

lint:
	ruff check .
	ruff format --check .
	mypy sql_ops_agent

clean:
	rm -rf build dist *.egg-info
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

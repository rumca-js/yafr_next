.PHONY: run install test format clean help

.DEFAULT_GOAL := run

# Python environment runner
PYTHON := poetry run python

## run: Start the YAFR Flask development server
run:
	@$(PYTHON) run.py

## install: Install all project dependencies via Poetry
install:
	@poetry install

## test: Run automated tests
test:
	@poetry run pytest -v

## format: Format Python codebase with black
format:
	@poetry run black yafr run.py

## clean: Clean compiled bytecode and caches
clean:
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf .pytest_cache 2>/dev/null || true

## help: Display this help message
help:
	@echo "YAFR - Yet Another Feed Reader"
	@echo "Available commands:"
	@sed -n 's/^##//p' $(MAKEFILE_LIST) | column -t -s ':'

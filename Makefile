# Convenience wrapper. Every target runs `python scripts/tasks.py <target>`, which works the same
# on Windows (PowerShell, no make needed), macOS and Linux. Run `make help` for the list.
PYTHON ?= python
TASKS := setup certs generate-proto lint format typecheck test test-integration frontend-check \
         check up down logs smoke-test clean

.PHONY: help $(TASKS)

help:
	@$(PYTHON) scripts/tasks.py

$(TASKS):
	@$(PYTHON) scripts/tasks.py $@ $(ARGS)

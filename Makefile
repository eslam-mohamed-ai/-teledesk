PYTHON ?= python
ALEMBIC = $(PYTHON) -m alembic -c backend/alembic.ini
export CONFIRM_EXISTING_SCHEMA

.PHONY: migrate stamp-existing lint typecheck test

migrate:
	$(ALEMBIC) upgrade head

stamp-existing:
	@$(PYTHON) -c "import os, sys; confirmed = os.getenv('CONFIRM_EXISTING_SCHEMA') == 'yes'; print('Schema confirmation required before stamping.' if not confirmed else 'Schema confirmation received.'); sys.exit(not confirmed)"
	$(ALEMBIC) stamp 202611220001
	$(ALEMBIC) upgrade head

lint:
	$(PYTHON) -m ruff check backend/app backend/migrations backend/tests

typecheck:
	$(PYTHON) -m mypy

test:
	$(PYTHON) -m pytest

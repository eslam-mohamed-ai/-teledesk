.PHONY: test test-lint test-mypy test-pytest

test: test-lint test-mypy test-pytest

test-lint:
	cd backend && ruff check app/

test-mypy:
	cd backend && mypy app/

test-pytest:
	cd backend && pytest tests/ -v

# Run full test suite against real Postgres+Redis via Docker Compose
docker-test:
	docker compose run --rm test

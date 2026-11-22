"""Dump the FastAPI OpenAPI schema to a file (default: stdout).

Usage:
    python scripts/dump_openapi.py ../frontend/openapi.json

Used by ``npm run gen:api`` to produce the typed frontend client. Importing the
app does not connect to the database, so this works offline.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app


def main() -> None:
    schema = app.openapi()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(schema, indent=2, sort_keys=True), encoding="utf-8")
    else:
        json.dump(schema, sys.stdout, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
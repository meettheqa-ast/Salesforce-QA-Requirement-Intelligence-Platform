"""Export the FastAPI OpenAPI schema to apps/api/openapi.json.

This is the source for TypeScript type generation in packages/shared-types.
Run offline (no server, no DB): it only introspects the app's route schema.

    uv run python scripts/export_openapi.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure the api package root (parent of scripts/) is importable when this file
# is run directly, regardless of the caller's working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import create_app  # noqa: E402


def main() -> None:
    app = create_app()
    schema = app.openapi()
    out = Path(__file__).resolve().parents[1] / "openapi.json"
    out.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

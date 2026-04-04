#!/usr/bin/env python3
"""CI lint script: verify all tool scripts in agents/ have INPUT_SCHEMA.

Usage:
    python scripts/lint_tools.py [agents_dir]

Exits 0 if all tool scripts define INPUT_SCHEMA.
Exits 1 if any tool script is missing INPUT_SCHEMA (prints errors to stderr).

Excludes files starting with _ (e.g., __init__.py, __pycache__).
"""
import importlib.util
import sys
from pathlib import Path


def lint_tools(agents_dir: str = "agents") -> list[str]:
    """Check all tool scripts for INPUT_SCHEMA. Returns list of error strings."""
    errors: list[str] = []
    agents_path = Path(agents_dir)

    if not agents_path.exists():
        return errors  # No agents dir = nothing to lint

    for tool_path in sorted(agents_path.glob("*/tools/[!_]*.py")):
        spec = importlib.util.spec_from_file_location(tool_path.stem, tool_path)
        if spec is None or spec.loader is None:
            errors.append(f"{tool_path}: cannot create module spec")
            continue

        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            errors.append(f"{tool_path}: import error -- {e}")
            continue

        if not hasattr(mod, "INPUT_SCHEMA"):
            errors.append(f"{tool_path}: missing INPUT_SCHEMA constant")

    return errors


def main() -> None:
    agents_dir = sys.argv[1] if len(sys.argv) > 1 else "agents"
    errors = lint_tools(agents_dir)

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    tool_count = len(list(Path(agents_dir).glob("*/tools/[!_]*.py")))
    print(f"OK: {tool_count} tool script(s) validated")


if __name__ == "__main__":
    main()

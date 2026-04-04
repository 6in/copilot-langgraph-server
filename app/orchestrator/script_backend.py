"""ScriptBackend: load and execute tool scripts with INPUT_SCHEMA validation.

Tool scripts live in agents/<name>/tools/*.py and expose:
- INPUT_SCHEMA: dict (JSON Schema) describing expected kwargs
- run(**kwargs) -> dict: the tool implementation

ScriptBackend validates kwargs against INPUT_SCHEMA before calling run().
If INPUT_SCHEMA is absent, validation is skipped (permissive for legacy tools).
"""
import importlib.util
from pathlib import Path

import jsonschema


class ScriptBackend:
    """Load a tool script module and call its run() with validated input."""

    def call(self, script_path: Path, kwargs: dict) -> dict:
        """Load script_path as a Python module, validate kwargs, call run().

        Args:
            script_path: Path to the tool .py file.
            kwargs: Input arguments to pass to run().

        Returns:
            The dict returned by the tool's run() function.

        Raises:
            ValueError: If kwargs fail INPUT_SCHEMA validation.
            AttributeError: If the module has no run() function.
            ImportError: If the module cannot be loaded.
        """
        spec = importlib.util.spec_from_file_location(
            f"tool_{script_path.stem}", script_path
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {script_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Validate against INPUT_SCHEMA if present (Pitfall 3: guard against None)
        schema = getattr(module, "INPUT_SCHEMA", None)
        if schema is not None:
            try:
                jsonschema.validate(instance=kwargs, schema=schema)
            except jsonschema.ValidationError as e:
                raise ValueError(f"Tool input validation failed: {e.message}") from e

        if not hasattr(module, "run"):
            raise AttributeError(
                f"Tool script {script_path} has no run() function"
            )

        return module.run(**kwargs)

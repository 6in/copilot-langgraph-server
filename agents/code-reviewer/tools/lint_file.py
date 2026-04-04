"""Lint a file for code quality issues.

Example tool script demonstrating the INPUT_SCHEMA convention.
INPUT_SCHEMA is a JSON Schema dict that describes the expected input kwargs.
ScriptBackend validates input against this schema before calling run().
"""

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "file_path": {
            "type": "string",
            "description": "Path to the file to lint",
        },
        "language": {
            "type": "string",
            "enum": ["python", "javascript", "typescript"],
            "description": "Programming language of the file",
        },
    },
    "required": ["file_path"],
    "additionalProperties": False,
}


def run(file_path: str, language: str = "python") -> dict:
    """Run linting on the specified file.

    Placeholder implementation for the INPUT_SCHEMA convention demo.
    """
    return {
        "file_path": file_path,
        "language": language,
        "issues": [],
        "status": "clean",
    }

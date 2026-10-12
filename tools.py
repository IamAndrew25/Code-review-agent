from pathlib import Path
import json

ROOT = (Path(__file__).parent / "target_project").resolve()


def _safe_path(relative_path):
    full = (ROOT / relative_path).resolve()
    if not full.is_relative_to(ROOT):
        raise ValueError("Path is outside the allowed folder")
    return full


def list_files(path="."):
    folder = _safe_path(path)
    return [p.name for p in sorted(folder.iterdir())]


def read_file(path):
    file = _safe_path(path)
    return file.read_text(encoding="utf-8")[:5000]


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Lists the files inside a folder of the project being reviewed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Folder path relative to the project root. Use '.' for the root.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads the text content of a file in the project being reviewed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to the project root, e.g. 'app.py'.",
                    }
                },
                "required": ["path"],
            },
        },
    },
]

AVAILABLE = {"list_files": list_files, "read_file": read_file}


def run_tool(name, arguments_json):
    try:
        args = json.loads(arguments_json or "{}")
        return str(AVAILABLE[name](**args))
    except Exception as error:
        return f"Error: {error}"
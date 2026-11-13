from pathlib import Path
import json

ROOT = (Path(__file__).parent / "target_project").resolve()
CHUNK_SIZE = 5000


def _safe_path(relative_path, root=None):
    root = Path(root or ROOT).resolve()
    full = (root / relative_path).resolve()
    if not full.is_relative_to(root):
        raise ValueError("Path is outside the allowed folder")
    return full


def list_files(path=".", root=None):
    folder = _safe_path(path, root)
    return [p.name + ("/" if p.is_dir() else "") for p in sorted(folder.iterdir())]


def read_file(path, offset=0, root=None):
    """Read a bounded character chunk. Offsets are Unicode character offsets."""
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise ValueError("offset must be a non-negative integer")
    content = _safe_path(path, root).read_text(encoding="utf-8")
    if offset > len(content):
        raise ValueError("offset is beyond the end of the file")
    end = min(offset + CHUNK_SIZE, len(content))
    return {"path": path, "offset": offset, "next_offset": end if end < len(content) else None,
            "total_characters": len(content), "start_line": content.count("\n", 0, offset) + 1,
            "content": content[offset:end]}


TOOLS = [
    {"type": "function", "function": {"name": "list_files", "description": "List files and folders (marked with /). Paths are relative to the project root.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read a file chunk. Continue with next_offset until it is null. start_line identifies the first line; chunks may split a line.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "offset": {"type": "integer", "minimum": 0}}, "required": ["path"]}}},
]


def run_tool(name, arguments_json):
    try:
        args = json.loads(arguments_json or "{}")
        return json.dumps({"list_files": list_files, "read_file": read_file}[name](**args), ensure_ascii=False)
    except (ValueError, OSError, KeyError, TypeError) as error:
        return json.dumps({"error": str(error)}, ensure_ascii=False)

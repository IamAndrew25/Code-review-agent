from tools import run_tool

print(run_tool("list_files", "{}"))
print(run_tool("read_file", '{"path": "app.py"}'))
print(run_tool("read_file", '{"path": "../tools.py"}'))
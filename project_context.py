"""Bounded Python import context. Parses code; never imports or executes it."""
import ast
from collections import deque
from pathlib import PurePosixPath

CONTEXT_LIMIT = 20000
PER_FILE_LIMIT = 6000


def module_name(path):
    parts = list(PurePosixPath(path).with_suffix('').parts)
    if parts[-1] == '__init__':
        parts.pop()
    return '.'.join(parts)


def build_graph(sources):
    modules = {module_name(p): p for p in sources if p.endswith('.py')}
    graph = {p: set() for p in sources}
    for path, source in sources.items():
        if not path.endswith('.py'):
            continue
        try:
            tree = ast.parse(source)
        except (SyntaxError, ValueError):
            continue
        package = module_name(path).split('.')
        if not path.endswith('/__init__.py') and path != '__init__.py':
            package = package[:-1]
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                prefix = package[:len(package) - node.level + 1] if node.level else []
                if node.module:
                    prefix += node.module.split('.')
                name = '.'.join(prefix)
                names = [name] + ['.'.join(filter(None, (name, alias.name))) for alias in node.names]
            for name in names:
                dependency = modules.get(name)
                if dependency and dependency != path:
                    # Include importers as well, so a sink can see its callers.
                    graph[path].add(dependency)
                    graph[dependency].add(path)
    return graph


def related_context(path, sources, graph, limit=CONTEXT_LIMIT):
    seen = {path}
    queue = deque([(path, 0)])
    sections, included, omitted, truncated = [], [], [], []
    used = 0
    while queue:
        current, depth = queue.popleft()
        if depth >= 2:
            continue
        for other in sorted(graph.get(current, ())):
            if other in seen:
                continue
            seen.add(other)
            queue.append((other, depth + 1))
            budget = min(PER_FILE_LIMIT, max(0, limit - used))
            if budget == 0:
                omitted.append(other)
                continue
            text = sources[other][:budget]
            used += len(text)
            if len(text) < len(sources[other]):
                truncated.append(other)
            included.append(other)
            numbered = '\n'.join(f'{i}: {line}' for i, line in enumerate(text.split('\n'), 1))
            sections.append(f'CONTEXT FILE: {other}\n{numbered}')
    return '\n\n'.join(sections), {'files': included, 'truncated': truncated, 'omitted': omitted}

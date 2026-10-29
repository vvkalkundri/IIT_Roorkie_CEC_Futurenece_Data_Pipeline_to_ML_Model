"""Safe, prepared workspaces for assignment experiments; no arbitrary paths."""
import re
from pathlib import Path


def workspace(project_root, conf):
    name = (conf or {}).get('observability_workspace')
    if name is None:
        return Path(project_root)
    if not isinstance(name, str) or not re.fullmatch(r'[a-z0-9_-]{1,80}', name):
        raise ValueError('Invalid observability workspace name')
    parent = (Path(project_root) / 'include/observability_workspaces').resolve()
    root = (parent / name).resolve()
    if root.parent != parent or not (root / '.prepared').is_file():
        raise ValueError('Observability workspace must be prepared before triggering')
    return root

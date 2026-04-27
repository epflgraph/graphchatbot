import re
from pathlib import Path


def resolve(name: str, path: Path, root: Path) -> str:
    """
    Find `{name}.md` by searching from `path` up to `root`, then load and
    recursively expand `{placeholder}` patterns within it.

    For each `{placeholder}` found, searches for `placeholder.md` using the
    same `path` and `root`. Raises FileNotFoundError if any file is not found.

    Use double braces `{{placeholder}}` for dynamic values to be filled in
    later via str.format; they are passed through as `{placeholder}`.
    """
    file = _find(name, start=path, root=root)
    if file is None:
        raise FileNotFoundError(
            f"No '{name}.md' found (searched from '{path}' up to '{root}')"
        )
    template = file.read_text()

    def replacer(match: re.Match) -> str:
        placeholder = match.group(1)
        return resolve(placeholder, path, root)

    result = re.sub(r'(?<!\{)\{(\w+)\}(?!\})', replacer, template)
    result = re.sub(r'\{\{(\w+)\}\}', r'{\1}', result)
    return result.strip()


def _find(name: str, start: Path, root: Path) -> Path | None:
    for directory in [start, *start.parents]:
        candidate = directory / f'{name}.md'
        if candidate.exists():
            return candidate
        if directory == root:
            break
    return None

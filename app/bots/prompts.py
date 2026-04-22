import re
from pathlib import Path


def resolve(file: Path, root: Path) -> str:
    """
    Load `file` and recursively expand `{name}` placeholders.

    For each `{name}` found, searches for `name.md` starting from the
    file's directory and walking up to `root`. Raises FileNotFoundError
    if no matching file is found.

    Use double braces `{{name}}` for dynamic placeholders that should
    be filled in later (e.g. via str.format at request time); they are
    passed through as `{name}` in the output.
    """
    template = file.read_text()

    def replacer(match: re.Match) -> str:
        name = match.group(1)
        fragment_file = _find(name, start=file.parent, root=root)
        if fragment_file is None:
            raise FileNotFoundError(
                f"No '{name}.md' found for placeholder '{{{name}}}' "
                f"in '{file}' (searched from '{file.parent}' up to '{root}')"
            )
        return resolve(fragment_file, root)

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

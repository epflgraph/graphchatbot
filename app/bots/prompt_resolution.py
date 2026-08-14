"""The pre-Jinja prompt loader: `{name}.md` files that `{placeholder}`-include
one another, resolved by walking a bot's directory tree. Explique has moved to
the Jinja environment in `app/compilation/templates.py`; this stays for the
families that haven't, and disappears once the last one migrates off it."""

import re
from functools import partial
from pathlib import Path


def _expand_placeholder(match: re.Match, *, start: Path, root: Path) -> str:
    """`re.sub`'s callback: resolve one `{placeholder}` match against the same search bounds."""
    return resolve(match.group(1), start, root)


def resolve(name: str, start: Path, root: Path) -> str:
    """
    Find `{name}.md` by searching from `start` up to `root`, then load and
    recursively expand `{placeholder}` patterns within it.

    For each `{placeholder}` found, searches for `placeholder.md` using the
    same `start` and `root`. Raises FileNotFoundError if any file is not found.

    Use double braces `{{placeholder}}` for dynamic values to be filled in
    later via str.format; they are passed through as `{placeholder}`.

    A placeholder is a Python identifier, so any template reachable this way
    must be named in snake_case — which is why `general_considerations.md` and
    `tool_description.md` are spelled differently from the kebab-case templates
    that only Jinja ever loads.
    """
    file_path = _find(name, start=start, root=root)
    if file_path is None:
        raise FileNotFoundError(f"No '{name}.md' found (searched from '{start}' up to '{root}')")
    template = file_path.read_text(encoding="utf-8")
    # Un-doubled `{placeholder}` first, recursively — a placeholder's own file
    # may itself contain further placeholders.
    result = re.sub(r"(?<!\{)\{(\w+)\}(?!\})", partial(_expand_placeholder, start=start, root=root), template)
    # Then unescape `{{placeholder}}` -> `{placeholder}`: untouched by the pass
    # above, so it survives to `Bot.prompt()`'s later `str.format()` call.
    result = re.sub(r"\{\{(\w+)\}\}", r"{\1}", result)
    return result.strip()


def _find(name: str, start: Path, root: Path) -> Path | None:
    """The path to `{name}.md`, searching from `start` up through `root`
    (inclusive), or None if it isn't found anywhere in that range."""
    for directory in [start, *start.parents]:
        candidate = directory / f"{name}.md"
        if candidate.exists():
            return candidate
        if directory == root:
            break
    return None

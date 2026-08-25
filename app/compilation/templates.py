from functools import lru_cache
from pathlib import Path

import jinja2

from app.compilation.examples import get_example_globals


@lru_cache
def _environment(search_path: tuple[Path, ...]) -> jinja2.Environment:
    """One environment per search path — never shared between bots, since the
    loader order and the examples globals are both bound to this one
    `search_path`; reusing another bot's environment would resolve prompts and
    examples against the wrong directories.

    Configures: the loader order that lets a course override a shared prompt;
    the settings that keep prompt text byte-faithful (no HTML-escaping, no
    silently-missing variables) and its whitespace exactly as written; and the
    examples globals every prompt can call.
    """
    environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader([str(directory) for directory in search_path]),
        # Prompt text is not markup: `<sources>` tags and quotes go through as written.
        autoescape=False,
        undefined=jinja2.StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    environment.globals.update(get_example_globals(search_path))
    return environment


def render_prompt(search_path: tuple[Path, ...], name: str, **context) -> str:
    """Render prompt template `name`, stripped so blocks compose predictably."""
    return _environment(search_path).get_template(name).render(**context).strip()

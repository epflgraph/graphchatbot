from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar

import jinja2
from pydantic import BaseModel


@lru_cache
def _environment(template_dir: Path, autoescape: bool) -> jinja2.Environment:
    """Shared Jinja settings for artifact templates.

    By default autoescape is on, since most artifacts produce HTML and every
    interpolated value is LLM-produced. Markdown artifacts can opt out so that
    their `<details>` blocks and the model's Markdown/LaTeX are preserved.
    """
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(template_dir)),
        autoescape=autoescape,
        undefined=jinja2.StrictUndefined,
    )


class Artifact(BaseModel, ABC):
    """Base for a bot response rendered from a Jinja template.

    A subclass points at its own template via `TEMPLATE_DIR`/`TEMPLATE_NAME`,
    chooses whether Jinja should HTML-escape interpolated values through
    `AUTOESCAPE`, and supplies the values it interpolates through `_context`.
    """

    TEMPLATE_DIR: ClassVar[Path]
    TEMPLATE_NAME: ClassVar[str]
    AUTOESCAPE: ClassVar[bool] = True

    def render(self) -> str:
        return (
            _environment(self.TEMPLATE_DIR, self.AUTOESCAPE).get_template(self.TEMPLATE_NAME).render(**self._context())
        )

    @abstractmethod
    def _context(self) -> dict[str, Any]:
        """The values this artifact's template interpolates."""

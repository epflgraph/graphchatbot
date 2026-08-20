from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar

import jinja2
from pydantic import BaseModel


@lru_cache
def _environment(template_dir: Path) -> jinja2.Environment:
    """Shared settings for every HTML artifact: autoescape is on, since every
    interpolated value is LLM-produced and must land as text, never as markup —
    unlike `app/compilation`'s environment, which renders prompt text, not markup."""
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(template_dir)),
        autoescape=True,
        undefined=jinja2.StrictUndefined,
    )


class Artifact(BaseModel, ABC):
    """Base for a bot response rendered as a standalone HTML page for the browser.

    A subclass points at its own template via `TEMPLATE_DIR`/`TEMPLATE_NAME` and
    supplies the values it interpolates through `_context`.
    """

    TEMPLATE_DIR: ClassVar[Path]
    TEMPLATE_NAME: ClassVar[str]

    def render(self) -> str:
        return _environment(self.TEMPLATE_DIR).get_template(self.TEMPLATE_NAME).render(**self._context())

    @abstractmethod
    def _context(self) -> dict[str, Any]:
        """The values this artifact's template interpolates."""

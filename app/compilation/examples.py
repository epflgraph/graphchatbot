from functools import lru_cache, partial
from pathlib import Path
from typing import Callable, TypedDict

import jinja2
import yaml
from pydantic import BaseModel, ConfigDict, model_validator
from typing_extensions import Self

EXAMPLES_DIRNAME = "examples"
EXAMPLES_SUFFIX = ".yaml"
MACRO_TEMPLATE = "macros/examples.md"


class Example(BaseModel):
    """One illustration. Each `tags` entry renders to a `<tag>text</tag>` block, in declaration order."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    slug: str  # a stable identity for every example, not just the ones addressed by name
    tags: dict[str, str]

    @model_validator(mode="after")
    def _assert_not_empty(self) -> Self:  # fail fast on an empty example
        if not any(text.strip() for text in self.tags.values()):
            raise ValueError(f"Example {self.slug!r} is empty; it needs at least one tag with text in it.")
        return self


class Examples(BaseModel):
    """The examples one prompt shows."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    examples: tuple[Example, ...]

    @model_validator(mode="after")
    def _example_slugs_are_unique(self) -> Self:
        seen = set()
        for example in self.examples:
            if example.slug in seen:
                raise ValueError(f"Duplicate example slug: {example.slug!r}")
            seen.add(example.slug)
        return self

    def get_example(self, slug: str) -> Example:
        """The example with this slug, in this set."""
        for example in self.examples:
            if example.slug == slug:
                return example
        raise UnknownExampleSlugError(slug, self)


class UnknownExampleSlugError(KeyError):
    """No example in this set has this slug."""

    def __init__(self, slug: str, examples: Examples):
        known = [example.slug for example in examples.examples]
        super().__init__(f"No example with slug {slug!r}. Known slugs: {known!r}")


class UndefinedExamplesError(KeyError):
    """No example set is defined under this name, anywhere on the search path."""

    def __init__(self, name: str, search_path: tuple[Path, ...]):
        super().__init__(
            f"No example set named {name!r} found on {list(search_path)!r}. "
            f"Add a `{EXAMPLES_DIRNAME}/{name}{EXAMPLES_SUFFIX}` file at one of these levels."
        )


@lru_cache
def load_example_set(search_path: tuple[Path, ...], name: str) -> Examples:
    """The example set named `name`, from the first directory in `search_path`
    that defines it — so a course-specific set overrides the shared one."""
    for directory in search_path:
        path = directory / EXAMPLES_DIRNAME / f"{name}{EXAMPLES_SUFFIX}"
        if path.is_file():
            return Examples.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    raise UndefinedExamplesError(name, search_path)


def all_example_sets(search_path: tuple[Path, ...]) -> tuple[Examples, ...]:
    """Every example set on `search_path`, one per name — if a name is defined
    in more than one directory, the most specific one wins. Used to validate
    the whole corpus at once, without rendering any particular prompt."""
    seen: dict[str, Examples] = {}
    for directory in search_path:
        examples_dir = directory / EXAMPLES_DIRNAME
        if not examples_dir.is_dir():
            continue
        for path in examples_dir.glob(f"*{EXAMPLES_SUFFIX}"):
            seen.setdefault(path.stem, load_example_set(search_path, path.stem))
    return tuple(seen.values())


def _interpolate(example_set: Examples, resolve: Callable[[str], str]) -> Examples:
    """The same set with every tag's text run through `resolve`, so example
    content can address the values its calling prompt can.

    Done here, not as a filter inside the macro: a macro loaded through
    `.module` runs in its own empty context, so the caller's context is no
    longer reachable by the time the macro runs.
    """
    return example_set.model_copy(
        update={
            "examples": tuple(
                example.model_copy(update={"tags": {tag: resolve(text) for tag, text in example.tags.items()}})
                for example in example_set.examples
            )
        }
    )


# `from_string` compiles a template from a plain string — needed because example
# text comes from YAML, not a file the loader can resolve by name. But unlike
# `get_template`, the environment doesn't cache what `from_string` compiles:
# every call re-lexes and re-compiles the same text from scratch. This cache
# stands in for that, so a repeated example isn't recompiled on every render —
# several times per prompt, on the user-visible streaming path. Keyed on the
# environment too, since a compiled template is bound to the one that built it.
@lru_cache(maxsize=512)
def _compile_text(environment: jinja2.Environment, text: str) -> jinja2.Template:
    return environment.from_string(text)


def _render_text(context: jinja2.runtime.Context, text: str) -> str:
    return _compile_text(context.environment, text).render(context.get_all())


def _resolve_example_set(context: jinja2.runtime.Context, search_path: tuple[Path, ...], name: str) -> Examples:
    return _interpolate(load_example_set(search_path, name), partial(_render_text, context))


def _macros(context: jinja2.runtime.Context):  # lazy: a bot with no examples/ must still work
    return context.environment.get_template(MACRO_TEMPLATE).module


def render_examples(
    search_path: tuple[Path, ...],
    context: jinja2.runtime.Context,
    name: str,
    framing: str | None = None,
) -> str:
    """The whole set as a section. `framing` names a template rendered under the
    heading — how to read *these* examples, which differs per kind of call."""
    framing_text = context.environment.get_template(framing).render(context.get_all()).strip() if framing else ""
    example_set = _resolve_example_set(context, search_path, name)
    return str(_macros(context).examples(example_set, framing_text)).strip()


def render_example(
    search_path: tuple[Path, ...],
    context: jinja2.runtime.Context,
    name: str,
    slug: str,
) -> str:
    """One example on its own, for prose that comments on it directly."""
    example_set = _resolve_example_set(context, search_path, name)
    return str(_macros(context).example(example_set.get_example(slug))).strip()


class ExampleGlobals(TypedDict):
    render_examples: Callable[..., str]
    render_example: Callable[..., str]


def get_example_globals(search_path: tuple[Path, ...]) -> ExampleGlobals:
    """The two globals a prompt template calls. Context-aware, so `_interpolate`
    sees what the calling template sees."""
    return ExampleGlobals(
        render_examples=jinja2.pass_context(partial(render_examples, search_path)),
        render_example=jinja2.pass_context(partial(render_example, search_path)),
    )

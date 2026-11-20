import logging
from collections.abc import Collection
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, ClassVar, Literal, get_args
from urllib.parse import parse_qsl, urlparse

from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from pydantic.json_schema import SkipJsonSchema
from typing_extensions import Self

from app.bots.artifacts.base import Artifact
from app.bots.artifacts.evaluation import EvaluationMetric, scan_urls
from app.utils import parse_int, time_label

logger = logging.getLogger(__name__)

# A MediaSpace page can't play inline, so its entry plays from SWITCH,
# the file it is served from, and the page stays linked under the player.
MEDIASPACE_HOST = "mediaspace.epfl.ch"
MEDIASPACE_ENTRY_PATH = "/media/t/"
MEDIASPACE_START = "kalturaStartTime"
SWITCH_HOST = "api.cast.switch.ch"
SWITCH_PLAY_PATH = "/playManifest/"
SWITCH_PLAY_URL = "https://api.cast.switch.ch/p/113/sp/11300/playManifest/entryId/{entry}/format/url/protocol/https/flavorParamIds/6,7"

# JSON reads a LaTeX command written with one backslash, such as `\frac` or `\theta`, as a control character.
CONTROL_CHARACTERS_AS_LATEX = str.maketrans({"\b": r"\b", "\f": r"\f", "\r": r"\r", "\t": r"\t"})
# A line break written with two backslashes, which JSON reads as the two characters `\n`.
LITERAL_LINE_BREAK = r"\n"
CODE_DELIMITER = "`"


def repair_escaping(text: str) -> str:
    """`text` as the model meant it, with the LaTeX commands and line breaks JSON escaping garbled put back."""
    spans = text.translate(CONTROL_CHARACTERS_AS_LATEX).split(CODE_DELIMITER)
    spans[::2] = map(_restore_line_breaks, spans[::2])  # the even spans are outside code
    return CODE_DELIMITER.join(spans)


def _restore_line_breaks(prose: str) -> str:
    restored, *pieces = prose.split(LITERAL_LINE_BREAK)
    for piece in pieces:
        # Before a lowercase letter it is a LaTeX command such as `\nu`, and after a backslash LaTeX's `\\`.
        literal = piece[:1].islower() or restored.endswith("\\")
        restored += (LITERAL_LINE_BREAK if literal else "\n") + piece
    return restored


# A block's text, with its LaTeX commands and line breaks restored.
BlockText = Annotated[str, AfterValidator(repair_escaping)]


class ResponseBlockType(StrEnum):
    TEXT = "text"
    COLLAPSIBLE = "collapsible"
    HINT = "hint"
    VIDEO = "video"


class ResponseBlock(Artifact):
    """One piece of a rich response, rendered through its own template."""

    model_config = ConfigDict(frozen=True)

    TEMPLATE_DIR = Path(__file__).parent / "templates"
    # Markdown, so the model's Markdown and LaTeX and the templates' tags go through as written.
    AUTOESCAPE = False
    # The evaluation a block must pass to be shown; one that fails is dropped from the reply.
    EVALUATION_METRICS: ClassVar[tuple[EvaluationMetric, ...]] = ()

    def _context(self) -> dict[str, Any]:
        return self.model_dump()


Sources = Annotated[
    tuple[str, ...],
    Field(description="The urls of the retrieved documents the block uses, copied exactly."),
]


class CitingBlock(ResponseBlock):
    """A block that cites the retrieved documents it uses, each one declaring `sources`."""

    numbers: SkipJsonSchema[tuple[int, ...]] = ()


class TextBlock(CitingBlock):
    """A paragraph the student sees as-is."""

    TEMPLATE_NAME = "text.md"

    type: Literal[ResponseBlockType.TEXT]
    sources: Sources
    content: BlockText = Field(..., description="Markdown and LaTeX, never HTML tags.")


class CollapsibleBlock(CitingBlock):
    """A titled block the student expands to read."""

    TEMPLATE_NAME = "collapsible.md"

    type: Literal[ResponseBlockType.COLLAPSIBLE]
    title: BlockText = Field(..., description="Plain text, never HTML tags, shown while the block is closed.")
    sources: Sources
    content: BlockText = Field(..., description="Markdown and LaTeX, never HTML tags.")


class HintBlock(CollapsibleBlock):
    """One progressive hint, which the student expands to read."""

    type: Literal[ResponseBlockType.HINT]


class VideoBlock(ResponseBlock):
    """A retrieved lecture video."""

    TEMPLATE_NAME = "video.md"
    EVALUATION_METRICS: ClassVar[tuple[EvaluationMetric, ...]] = (scan_urls,)

    type: Literal[ResponseBlockType.VIDEO]
    url: str = Field(..., description="The video's url, copied exactly.")

    def _context(self) -> dict[str, Any]:
        """What the player plays and what the link under it opens."""
        url = urlparse(self.url)
        if url.hostname == MEDIASPACE_HOST and url.path.startswith(MEDIASPACE_ENTRY_PATH):
            query = dict(parse_qsl(url.query))
            start = parse_int(query.get(MEDIASPACE_START, "0"))
            if start is not None:
                entry = url.path.removeprefix(MEDIASPACE_ENTRY_PATH)
                player = f"{SWITCH_PLAY_URL.format(entry=entry)}#t={start}"
                return {"player": player, "link": self.url, "timestamp": time_label(start)}
        if url.hostname == SWITCH_HOST and SWITCH_PLAY_PATH in url.path:
            return {"player": self.url, "link": None, "timestamp": None}
        return {"player": None, "link": self.url, "timestamp": None}


class RichResponse(BaseModel):
    """A reply as an ordered sequence of blocks."""

    model_config = ConfigDict(frozen=True)

    # What a reply's blocks are joined with, on the stream and in the transcript alike.
    BLOCK_SEPARATOR: ClassVar[str] = "\n\n"

    blocks: tuple[ResponseBlock, ...]

    @classmethod
    def block_schemas(cls) -> tuple[dict[str, Any], ...]:
        """The JSON schema of each block this reply offers, in the order `blocks` lists them."""
        block_union = get_args(cls.model_fields["blocks"].annotation)[0]
        block_classes = get_args(block_union) or (block_union,)
        return tuple(block.model_json_schema() for block in block_classes)

    def cited_urls(self, retrieved_urls: Collection[str]) -> tuple[str, ...]:
        """The retrieved urls the reply cites, in the order first cited."""
        cited = []
        for block in self.blocks:
            if isinstance(block, CitingBlock):
                for url in block.sources:
                    if url in retrieved_urls:
                        cited.append(url)
                    else:
                        # An invented or withheld url costs its chip, not what the block says.
                        logger.warning("A %s block cites %r, which is not a source it may cite", block.type, url)
        return tuple(dict.fromkeys(cited))  # drops repeats, keeps first-cited order

    def with_numbered_citations(self, cited_urls: tuple[str, ...]) -> Self:
        """The reply with each citing block's `numbers` set: a url's number is its place in `cited_urls`."""
        # Open WebUI numbers sources across the whole reply, so a block can't number its own.
        blocks = []
        for block in self.blocks:
            if isinstance(block, CitingBlock):
                numbers = sorted({cited_urls.index(url) + 1 for url in block.sources if url in cited_urls})
                block = block.model_copy(update={"numbers": tuple(numbers)})
            blocks.append(block)
        return self.model_copy(update={"blocks": tuple(blocks)})

    def render(self) -> str:
        """The reply as the student reads it: each block rendered, in order."""
        return self.BLOCK_SEPARATOR.join(block.render() for block in self.blocks)

import inspect
from abc import ABC, abstractmethod
from datetime import datetime
from functools import cached_property
from pathlib import Path

from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.state import CompiledStateGraph

from app.compilation.base import ModelChoice
from app.config import config
from app.identity import Requester

BOTS_ROOT = Path(__file__).parent

# What a level's prompt templates are kept in, at every level of the bot tree.
PROMPTS_DIRNAME = "prompts"


class BotState(MessagesState):
    category: str | None
    tool_choice: str | None

    # Who is asking, when the frontend forwards it. None when it does not.
    requester: Requester | None

    # The tool loop, shared by every family: `active_node` is where `tools`
    # sends control back to, written by whichever model node issued the calls;
    # `tool_round` counts the rounds that node has taken this turn.
    active_node: str | None
    tool_round: int


# A node's return value: a partial update merged into the graph state by
# LangGraph (fields omitted are left untouched; `messages` is appended to
# rather than overwritten, per BotState's `add_messages` reducer).
StateUpdate = dict


class Bot(ABC):
    """A servable bot: its identity, its clients, and the graph that runs a turn.

    Every concrete bot must define:
        name: str          — how it is served and registered; must be unique
        groups: list[str]  — the groups allowed to use it (empty for everyone)
        build_graph()      — the compiled LangGraph a turn runs through

    and may override:
        reply_model / fast_model / careful_model / vision_model — the clients for the reply,
                              quick calls, calls where accuracy beats speed, and images
        model_nodes         — which nodes' tokens are streamed to the user (a node can
                              also stream text itself, through `runtime.stream_writer`)
        prompt_context()    — values every one of its prompts can use

    Intermediate classes that exist to share behaviour rather than to be served
    define no `name`, which is how `registry.init_bots` tells them apart from a
    bot it should register.
    """

    name: str
    groups: list[str]

    reply_model: ChatOpenAI = ChatOpenAI(
        base_url=config.rcp.base_url,
        model="Qwen/Qwen3.6-35B-A3B",
        api_key=config.rcp.api_key,
        timeout=60,
        max_retries=1,
        stream_usage=True,
        temperature=0.7,
        top_p=0.8,
        presence_penalty=1.5,
        extra_body={
            "top_k": 20,
            "min_p": 0.0,
            "repetition_penalty": 1.0,
            "chat_template_kwargs": {"enable_thinking": False},
        },
    )

    fast_model: ChatOpenAI = reply_model
    # Unlike fast_model, these have no fallback client — see `model_for` for why.
    careful_model: ChatOpenAI | None = None
    vision_model: ChatOpenAI | None = None

    model_nodes: tuple[str, ...] = ("model",)

    @cached_property
    def directory(self) -> Path:
        """The directory this bot's own files live in."""
        return Path(inspect.getfile(type(self))).parent

    @cached_property
    def prompt_levels(self) -> tuple[Path, ...]:
        """The levels a prompt can be defined at: this bot's own directory, then
        each parent up to and including `BOTS_ROOT`."""
        levels = []
        for level in [self.directory, *self.directory.parents]:
            levels.append(level)
            if level == BOTS_ROOT:
                return tuple(levels)

        # A subclass defined outside BOTS_ROOT would otherwise collect every
        # ancestor up to `/`, and load any same-named template sitting in one.
        raise ValueError(f"{type(self).__name__} is defined at {self.directory}, which is not under {BOTS_ROOT}.")

    @cached_property
    def prompt_search_path(self) -> tuple[Path, ...]:
        """Where this bot's prompt templates are looked up: each level's
        `prompts/`, innermost first. A course's own copy of a template
        shadows the family's, which shadows the shared one."""
        return tuple(level / PROMPTS_DIRNAME for level in self.prompt_levels)

    def model_for(self, choice: ModelChoice) -> ChatOpenAI:
        """The client a call of this choice runs on.

        Looked up rather than branched, so a new `ModelChoice` no bot serves
        raises instead of quietly getting the fast one. A bot that declares no
        `vision_model` raises too: unlike `fast_model`, whose default is the
        same modality and so harmless, silently answering a vision call with a
        text client sends image parts to an endpoint that cannot read them.
        So does one with no `careful_model`: a call that asked for the careful
        client would otherwise run, unnoticed, on a less accurate one.
        """
        model = {
            ModelChoice.REPLY: self.reply_model,
            ModelChoice.FAST: self.fast_model,
            ModelChoice.CAREFUL: self.careful_model,
            ModelChoice.VISION: self.vision_model,
        }[choice]

        if model is None:
            raise NotImplementedError(f"Bot {self.name!r} declares no {choice} model, but a call asked for one.")
        return model

    def prompt_context(self) -> dict:
        return {"today": datetime.now().strftime("%Y-%m-%d")}

    @abstractmethod
    def build_graph(self) -> CompiledStateGraph: ...

    @cached_property
    def graph(self) -> CompiledStateGraph:
        return self.build_graph()

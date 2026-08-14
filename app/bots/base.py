import inspect
from abc import ABC, abstractmethod
from datetime import datetime
from functools import cached_property
from pathlib import Path

from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.state import CompiledStateGraph

from app.bots.prompt_resolution import resolve
from app.compilation.base import ModelChoice
from app.config import config
from app.llms.utils import DialogView

BOTS_ROOT = Path(__file__).parent

# What a level's prompt templates are kept in, at every level of the bot tree.
PROMPTS_DIRNAME = "prompts"


class BotState(MessagesState):
    category: str | None
    tool_choice: str | None


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
        model / light_model / vision_model — the streaming, deterministic, and vision clients
        model_nodes         — which nodes' tokens reach the user
        dialog              — how a transcript is compiled before it reaches a prompt
        DEFAULT_PROMPT_NAME — the template `prompt()` resolves when given no name
        prompt_context()    — values every one of its prompts can use

    Intermediate classes that exist to share behaviour rather than to be served
    define no `name`, which is how `registry.init_bots` tells them apart from a
    bot it should register.
    """

    name: str
    groups: list[str]

    model: ChatOpenAI = ChatOpenAI(
        base_url=config.rcp.base_url,
        model="Qwen/Qwen3.6-35B-A3B",
        api_key=config.rcp.api_key,
        timeout=60,
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

    light_model: ChatOpenAI = model
    # Unlike light_model, no fallback client — see `model_for` for why.
    vision_model: ChatOpenAI | None = None

    model_nodes: tuple[str, ...] = ("model",)

    # How this bot wrangles a conversation before it reaches a prompt. The
    # default view has no callbacks, so a transcript compiles verbatim.
    dialog: DialogView = DialogView()

    # A family that leads with a different template sets this, rather than
    # overriding `prompt()` just to change a string.
    DEFAULT_PROMPT_NAME: str = "prompt"

    @cached_property
    def prompt_directories(self) -> tuple[Path, ...]:
        """The levels a prompt can be defined at: this bot's own directory, then
        each parent up to and including `BOTS_ROOT`."""
        start = Path(inspect.getfile(type(self))).parent
        directories = []
        for directory in [start, *start.parents]:
            directories.append(directory)
            if directory == BOTS_ROOT:
                return tuple(directories)

        # A subclass defined outside BOTS_ROOT would otherwise collect every
        # ancestor up to `/`, and load any same-named template sitting in one.
        raise ValueError(f"{type(self).__name__} is defined at {start}, which is not under {BOTS_ROOT}.")

    @cached_property
    def prompt_search_path(self) -> tuple[Path, ...]:
        """Where this bot's prompt templates are looked up: each level's
        `prompts/` before the level itself, innermost first. A course's own copy
        of a template therefore shadows the family's, which shadows the shared
        one.

        The bare level stays in the path because the fragments `prompt()`
        expands still live there: `resolve` walks directories and cannot see
        into a `prompts/` subdirectory, so those cannot move while it exists.
        """
        return tuple(path for level in self.prompt_directories for path in (level / PROMPTS_DIRNAME, level))

    def model_for(self, choice: ModelChoice) -> ChatOpenAI:
        """The client a call of this choice runs on.

        Looked up rather than branched, so a new `ModelChoice` no bot serves
        raises instead of quietly getting the light one. A bot that declares no
        `vision_model` raises too: unlike `light_model`, whose default is the
        same modality and so harmless, silently answering a vision call with a
        text client sends image parts to an endpoint that cannot read them.
        """
        model = {
            ModelChoice.MAIN: self.model,
            ModelChoice.LIGHT: self.light_model,
            ModelChoice.VISION: self.vision_model,
        }[choice]

        if model is None:
            raise NotImplementedError(f"Bot {self.name!r} declares no {choice} model, but a call asked for one.")
        return model

    def prompt_context(self) -> dict:
        return {"today": datetime.now().strftime("%Y-%m-%d")}

    def prompt(self, name: str | None = None) -> str:
        """The named prompt template, filled in. `name` is optional so a caller
        holding a "not specified" value can pass it straight through."""
        template = resolve(name or self.DEFAULT_PROMPT_NAME, self.prompt_directories[0], BOTS_ROOT)
        return template.format(**self.prompt_context())

    @abstractmethod
    def build_graph(self) -> CompiledStateGraph: ...

    @cached_property
    def graph(self) -> CompiledStateGraph:
        return self.build_graph()

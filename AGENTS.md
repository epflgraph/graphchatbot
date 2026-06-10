# GraphChatBot — Agent Reference

## Active Refactor (In Progress)

The codebase is transitioning from a legacy `app/integrations/` system to a new `app/bots/` architecture.

- **New code** → `app/bots/`
- **Legacy code** → `app/integrations/` (being deprecated, do not add to it)
- **Goal**: Each bot is a self-contained class under `app/bots/`, discovered at runtime by scanning for `*_bot.py` files

## Architecture

```
app/
├── main.py              # FastAPI entry point
├── config.py            # INI + env loading
├── bots/
│   ├── base.py          # Bot ABC, BotState, model config
│   ├── registry.py      # Filesystem-scan bot discovery
│   ├── prompts.py       # Recursive markdown prompt resolution
│   ├── main.py          # generate_completion / agenerate_completion (streaming)
│   ├── nodes/           # Reusable LangGraph nodes (classify, model, tools)
│   ├── admin/           # AdminBot + concrete admin bots
│   ├── course/          # CourseBot + HintingCourseBot / DirectCourseBot + concrete course bots
│   └── graph_chat/      # GraphChatBot
├── interfaces/graphai.py # GraphAI RAG client (graphai singleton)
├── llms/utils.py        # Structured output helpers
└── routers/             # FastAPI routers
```

## Adding a New Bot

1. Pick the right parent class:
   - `AdminBot` — single-tool RAG bot for institutional docs
   - `CourseBot` — course tutor with theory/practice/admin/unrelated classification
   - `HintingCourseBot` — course tutor that gives hints first, not direct answers
   - `DirectCourseBot` — course tutor that gives direct answers
   - Or subclass `Bot` directly for custom topologies

2. Create a directory: `app/bots/<category>/<botname>/`

3. Add files:
   - `*_bot.py` — class definition (must set `name: str`, `groups`, and required fields)
   - `course_name.md` — short name used in prompts
   - `coursebook.md` — course details/content for prompts
   - `tool_notes.md` — optional, course-specific tool-calling notes

4. Restart — registry auto-discovers it. No manual registration needed.

## Prompt System

Prompts are Markdown files resolved recursively by `app/bots/prompts.py`:

- `{fragment}` → inline another `.md` file (searches from bot dir up to `app/bots/`)
- `{{placeholder}}` → dynamic value filled later via `str.format(...)`

Example `app/bots/course/prompt.md`:
```markdown
You are a supportive AI tutor for "{course_name}", a course at EPFL.

{coursebook}

{pedagogical_considerations}

{format}

{general_considerations}
```

Each fragment is resolved by walking up the directory tree, so a bot can override a shared fragment locally or fall back to the parent one.

## Key Conventions

- **Async everywhere**: Node functions and tools are `async`
- **Type hints**: Use `list[str]`, `dict[str, ...]`, `str | None` (Python 3.11+)
- **Models**: `langchain_openai.ChatOpenAI`, configured via `app.config.config`
- **Graphs**: Stateless, compiled at startup via `@cached_property`, reused per request
- **Streaming**: Use `stream_mode="messages"`, filter by `metadata["langgraph_node"]`
- **Tools**: Declare via `langchain.tools.tool`, with Pydantic `args_schema`
- **State**: Extend `BotState` (adds `category` and `tool_choice` to `MessagesState`)
- **Config access**: `config.get("section", {}).get("key")` — never hardcode credentials
- **Logging**: Use `logging.getLogger(__name__)`; structured logs via `app.logging_config`

## Running Locally

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -e .

# Config
cp config.ini.example config.ini  # edit with your credentials

# Run
python -m app.main
# or
uvicorn app.main:app --reload --port 8000
```

## Testing a Bot

```python
from app.bots.registry import init_bots, get_bot
init_bots()
b = get_bot('BOT-NAME')
print(b.prompt())      # Check prompt resolution
print(b.build_tools()) # Check tool schema
b.graph                # Verify graph compiles
```

## Important Notes

- Do **not** modify `app/integrations/` — it is legacy
- Do **not** add bots to a manual registry — discovery is automatic
- Do **not** hardcode model names or API keys — use `config.ini` / `.env`
- Never read config files.
- Bot names must be unique; duplicates log a warning and overwrite
- Abstract bot classes (no `name` attribute) are skipped by the registry

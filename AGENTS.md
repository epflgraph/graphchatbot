# EPFL Graph and CEDE Chatbots — Agent Reference

## Recent Refactor

The codebase was refactored from a legacy `app/integrations/` system to the current `app/bots/` architecture.

- **Current code** → `app/bots/` (active)
- **Legacy code** → `app/integrations/` (retained for reference, do not add to it)
- **Architecture**: Each bot is a self-contained class under `app/bots/`, discovered at runtime by scanning for `*_bot.py` files

## Architecture

```
app/
├── main.py              # FastAPI entry point
├── config.py            # INI loading, validated through a frozen Pydantic model
├── compilation/         # Message compilation: Jinja templates, example banks, bounded model calls
├── bots/
│   ├── base.py          # Bot ABC, BotState, model configuration
│   ├── registry.py      # Auto-discovery of bot classes via filesystem scanning
│   ├── languages.py     # Languages a bot can be instructed to reply in
│   ├── main.py          # LLM completion / streaming helpers
│   ├── compilers/       # Shared message compilers (classify, respond)
│   ├── prompts/         # Shared prompt templates and macros
│   ├── nodes/           # Reusable LangGraph nodes (classify, model, tools, transcribe_image, detect_language)
│   ├── artifacts/       # Base for bot responses rendered as HTML
│   ├── cache/           # Shared on-disk caches (e.g. image transcriptions)
│   ├── admin/           # AdminBot + concrete admin bots
│   ├── course/          # CourseBot + pedagogical variants
│   ├── explique/        # ExpliqueBot Socratic tutors + course variants
│   └── graph_chat/      # GraphChatBot
├── interfaces/graphai.py # GraphAI RAG client
├── llms/utils.py        # Message shaping helpers (flattening, image parts, timeouts)
└── routers/             # FastAPI public routers
```

## Adding a New Bot

1. Pick the right parent class:
   - `AdminBot` — single-tool RAG bot for institutional docs
   - `CourseBot` — course tutor with built-in message classification (greeting / theory / practice / admin / unrelated)
   - `HintingCourseBot` — course tutor that provides hints instead of direct answers
   - `DirectCourseBot` — course tutor that gives direct answers
   - `ExpliqueBot` — Socratic tutor that has the student explain concepts back, and responds to each explanation
   - `Bot` (ABC) — fully custom LangGraph topology

2. Create a directory: `app/bots/<category>/<botname>/`

3. Add files:
   - `<botname>_bot.py` — class definition (must set `name: str`, `groups: list[str]`, and any required fields)
   - `prompts/<template>.md` — prompt templates for the agent, or omit as needed to fall back to higher-level ones
   - `prompts/tool-description.md` — tool-calling hints

4. Restart — registry auto-discovers it. No manual registration needed.

## Prompt Rendering

Prompts are Jinja templates resolved by `app.compilation.templates.render_prompt` along `Bot.prompt_search_path`, which runs from the bot's own directory upwards:

- `{% include %}` → pull in another template, taking the first match on the search path
- `{{ placeholder }}` → dynamic value filled at runtime from `Bot.prompt_context()` plus the per-call context the compiler builds
- `{{ render_examples("name") }}` / `{{ render_example("name", "slug") }}` → render an example bank from `prompts/examples/name.yaml`, optionally framed by a `framing="...md"` template

Templates render under `StrictUndefined`, so a placeholder with no value raises rather than rendering empty.

## Key Conventions

- **Async everywhere**: Node functions and tools are `async`
- **Type hints**: Use `list[str]`, `dict[str, ...]`, `str | None` (Python 3.12)
- **Models**: `langchain_openai.ChatOpenAI`. Credentials (`base_url`, `api_key`) are read from `config.ini`; the shared base model name and generation parameters in `app.bots.base.Bot` are currently hardcoded.
- **Graphs**: Stateless, compiled at startup via `@cached_property`, reused per request
- **Streaming**: Use `stream_mode="messages"`, filter by `metadata["langgraph_node"]`
- **Tools**: Declare via `langchain.tools.tool`, with Pydantic `args_schema`
- **State**: Extend `BotState` (adds `category`, `tool_choice`, `active_node`, and `tool_round` to `MessagesState`)
- **Config access**: Use the typed `app.config.config` object, e.g. `config.rcp.api_key` — never hardcode credentials
- **Logging**: Use `logging.getLogger(__name__)`; structured logs via `app.logging_config`
- **Languages**: Reuse `app.bots.languages.LANGUAGES` and `no_answer(lang_code)` for supported reply languages and failure messages

## Running Locally

```bash
# Setup
make install       # runtime only
make install-dev   # adds linting and pre-commit hooks

# Config
cp config.ini.example config.ini  # edit with your credentials

# Run
python -m app.main
# or
uvicorn app.main:app --reload --port 8000
```

## API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/chat/completions` | OpenAI-compatible completion; set `"stream": true` for SSE |
| `GET` | `/models` | Lists the registered bots |

Both routes are also served under `/v1`, so a stock OpenAI client works against them unmodified:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="unused")
client.chat.completions.create(model="MY-BOT-NAME", messages=[{"role": "user", "content": "Hi"}])
```

## Testing a Bot

```python
from app.bots.registry import init_bots, get_bot, list_bots
from app.compilation.templates import render_prompt

init_bots()
bot = get_bot("MY-BOT-NAME")

print(bot.prompt_search_path)  # Where its templates resolve from, nearest first
print(render_prompt(bot.prompt_search_path, "classify-sys.md", **bot.prompt_context()))
print(bot.build_tools())       # Inspect tool schemas
print(bot.graph)               # Verify graph compiles
```

`list_bots()` returns every registered bot if you would rather scan them all.

### Run the Checks

```bash
make test      # run unittest discover over tests/ with coverage
make lint      # check linting and formatting (no writes)
make lint-fix  # auto-fix lint issues and reformat
```

## Important Notes

- Do **not** modify `app/integrations/` — it is legacy
- Do **not** add bots to a manual registry — discovery is automatic
- Do **not** hardcode API keys — use `config.ini` / `.env`
- Never commit config files or secrets
- Bot names must be unique; duplicates log a warning and overwrite
- Abstract bot classes (no `name: str` attribute) are skipped by the registry

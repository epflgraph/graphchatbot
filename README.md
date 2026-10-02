# EPFL Graph and CEDE Chatbots

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/epflgraph/graphchatbot/actions/workflows/ci.yaml/badge.svg)](https://github.com/epflgraph/graphchatbot/actions/workflows/ci.yaml)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)

This is the FastAPI backend for the EPFL Graph and CEDE chatbots, developed by the [Center for Digital Education (CEDE)](https://www.epfl.ch/education/educational-initiatives/cede/): a modular framework to build and serve educational tutors, the EPFL Graph chatbot and other administrative RAG assistants. All bots are built with [LangChain](https://python.langchain.com/) and [LangGraph](https://langchain-ai.github.io/langgraph/).

The system is designed around a modular, self-discovering **bot architecture**: each bot is a standalone agent with its own prompts, tools, and conversation graph. New bots are automatically detected at runtime—no manual registration required.

All agents use models from the inference service at EPFL's [Research Computing Platform](https://portal.rcp.epfl.ch), which guarantees that data is never sent to external providers.

---

## Overview

This repository exposes a **FastAPI** application with OpenAI-compatible streaming endpoints that serve a variety of task-specific AI tutors and assistants. Bots can be tailored for:

- **Administrative tasks** (e.g. answering questions about institutional docs via RAG)
- **Course tutoring** (e.g. pedagogical Q&A, with each turn classified as greeting / theory / practice / admin / unrelated)
- **Learning by explaining** (the student explains the material back, and the tutor responds to the
  explanation instead of providing the answer; a graded flavour records each topic a student covers
  in Moodle)
- **Custom workflows** (build any LangGraph topology and plug it in)

---

## Project Architecture

```
app/
├── main.py              # FastAPI entry point
├── config.py            # INI loading, validated through a frozen Pydantic model
├── logging_config.py    # Logging setup and Sentry incident reporting
├── identity.py          # Who is asking, read from the headers the chat frontend forwards
├── utils.py             # Small string helpers
├── compilation/         # Message compilation: Jinja templates, example banks, bounded model calls
├── bots/
│   ├── base.py          # Bot ABC, BotState, model configuration
│   ├── registry.py      # Auto-discovery of bot classes via filesystem scanning
│   ├── languages.py     # Languages a bot can be instructed to reply in
│   ├── main.py          # LLM completion / streaming helpers
│   ├── utils.py         # Status events and text a node writes to the stream itself
│   ├── compilers/       # Shared message compilers (classify, respond)
│   ├── prompts/         # Shared prompt templates and macros
│   ├── nodes/           # Reusable LangGraph nodes (classify, model, tools, transcribe_image, detect_language)
│   ├── artifacts/       # Base for bot responses rendered as HTML
│   ├── cache/           # Shared on-disk caches (e.g. image transcriptions, topic points)
│   ├── admin/           # AdminBot + concrete admin bots
│   ├── course/          # CourseBot + pedagogical variants
│   ├── explique/        # ExpliqueBot base + its train/ and grade/ flavours
│   └── graph_chat/      # GraphChatBot
├── interfaces/          # Clients for external services (GraphAI RAG, Moodle)
├── llms/utils.py        # Message shaping helpers (flattening, image parts, timeouts)
└── routers/             # FastAPI public routers
```

### Key Design Decisions

- **Auto-discovery**: Bots are found by scanning `app/bots/` for classes defined in `*_bot.py` files
- **No central registry**: Drop a new bot directory in the right place and restart—the registry picks it up automatically
- **Prompts as templates**: Prompts are Jinja templates resolved along a per-bot search path, allowing easy inheritance and overrides
- **Typed configuration**: `config.ini` is validated against a frozen Pydantic model at startup, so a bad key fails fast
- **Stateless graphs**: LangGraph graphs are compiled once at startup (`@cached_property`) and reused per request
- **Streaming-first**: All bots support streaming message completion via `stream_mode=["messages", "custom"]`; a node can also write a status event or text to the stream itself through `runtime.stream_writer`

---

## Getting Started

### Prerequisites

- **Python** 3.12
- A running RAG backend (GraphAI / Elasticsearch) if using RAG-enabled bots
- An [RCP API key](https://portal.rcp.epfl.ch)
- A Moodle web-service token if serving graded explique bots
- A chat frontend that forwards the user's identity, for bots that need to know who is asking
  (Open WebUI with `ENABLE_FORWARD_USER_INFO_HEADERS` on)

### Installation

```bash
# Clone the repository
git clone https://github.com/epflgraph/graphchatbot.git
cd graphchatbot

# Install dependencies (installs uv if needed, then syncs the environment)
make install       # runtime only
make install-dev   # adds linting and pre-commit hooks
```

### Configuration

Copy the example configuration file and fill in your credentials:

```bash
cp config.ini.example config.ini
```

Edit `config.ini` to set:

| Section | Required | Contents |
|---------|----------|----------|
| `[rcp]` | yes | Inference base url and API key |
| `[elasticsearch]` | yes | Search index, plus connection details |
| `[graphsearch]` | yes | GraphSearch base url |
| `[graphai]` | yes | GraphAI RAG connection details |
| `[cache]` | no | Root for on-disk caches; empty falls back under the system temp dir |
| `[langfuse]` | no | Credentials for tracing |
| `[sentry]` | no | DSN and environment for error reporting; an empty DSN disables it |
| `[moodle]` | no | Moodle base url and web-service token (both or neither); graded explique bots need it |
| `[moodle_polling]` | no | Seconds between the passes that keep graded courses' topics in step with Moodle |

The file is validated against a frozen Pydantic model at startup, so a missing required section
or an unrecognised key raises immediately instead of being silently ignored.

### Running Locally

```bash
# Standard
python -m app.main

# With auto-reload (development)
uvicorn app.main:app --reload --port 8000
```

The API documentation will be available at `http://localhost:8000/docs`.

### API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/chat/completions` | OpenAI-compatible completion; set `"stream": true` for SSE |
| `GET` | `/models` | Lists the registered bots |

`model` selects the bot by its `name`. Both routes are also served under `/v1`, so a stock
OpenAI client works against them unmodified:

```python
from openai import OpenAI

# This service does not check the key, but the SDK requires one to be set.
client = OpenAI(base_url="http://localhost:8000/v1", api_key="unused")
client.chat.completions.create(model="MY-BOT-NAME", messages=[{"role": "user", "content": "Hi"}])
```

The `X-OpenWebUI-User-Id` and `X-OpenWebUI-User-Email` headers, when the chat frontend forwards
them, tell a bot who is asking. They are unverified, and without them the bot sees no requester.

A streamed reply can also carry status events: chunks with an `event` object, which Open WebUI
shows as a line above the reply until its text arrives.

---

## Adding a New Bot

Creating a new bot requires **zero** modifications to existing code.

1. **Create the bot directory**  
   Inside `app/bots/<category>/<botname>/`, create:
   - `<botname>_bot.py` — class definition
   - `prompts/<template>.md` — prompt templates for the agent, or omit as needed to fall back to higher-level ones
   - `prompts/tool-description.md` — tool-calling hints

2. **Pick the right base class**

   | Base Class | Use Case |
   |------------|----------|
   | `AdminBot` | Single-tool RAG bot for institutional docs |
   | `CourseBot` | Course tutor with built-in message classification (greeting / theory / practice / admin / unrelated) |
   | `HintingCourseBot` | Course tutor that provides hints instead of direct answers |
   | `DirectCourseBot` | Course tutor that gives direct answers |
   | `DebateCourseBot` | Course tutor that uses a peer-debate pedagogical style |
   | `ExpliqueTrainBot` | Socratic tutor that has the student explain concepts back, and responds to each explanation |
   | `ExpliqueGradeBot` | Graded flavour of explique: the student picks one topic, and covering it is recorded in Moodle |
   | `Bot` (ABC) | Fully custom LangGraph topology |

   Each bot class **must** define:
   - `name: str` (unique identifier)
   - `groups: list[str]` (the groups allowed to use it; `[]` for unrestricted). Declared for the
     caller in front of this service — the API itself does not enforce it
   - Any required configuration fields (e.g. `index` for a course's material, `course_id` for a
     graded bot's Moodle course)

3. **Restart the application** — the registry auto-discovers and instantiates the bot.

### Prompt Rendering

The compilation layer (`app/compilation/`) builds each bot's messages from Jinja templates
resolved along `Bot.prompt_search_path`, which runs from the bot's own directory upwards:

- `{% include %}` → pull in another template, taking the first match on the search path
- `{{ placeholder }}` → dynamic value filled at runtime from `Bot.prompt_context()` plus the
  per-call context the compiler builds
- `{{ render_examples("name") }}` / `{{ render_example("name", "slug") }}` → render an example
  bank from `prompts/examples/name.yaml`, optionally framed by a `framing="...md"` template

Templates render under `StrictUndefined`, so a placeholder with no value raises rather than
rendering empty.

---

## Testing

### Inspect a Bot

```python
from app.bots.registry import init_bots, get_bot
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

---

## Development Guidelines

- **Async everywhere**: All node functions and tools must be `async`
- **Python 3.12 types**: Use `list[str]`, `dict[str, ...]`, `str | None`
- **No hardcoded secrets**: Always pull from `config.ini` / `.env` via the typed config, e.g. `config.rcp.api_key`
- **Logging**: Use `logging.getLogger(__name__)`; the logging format is configured in `app.logging_config`

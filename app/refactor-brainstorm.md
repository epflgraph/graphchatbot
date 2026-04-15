# GraphChatbot Refactor — Brainstorm Notes

## Goals
- Reduce boilerplate: adding a new course bot should take ~30 lines, not ~380
- Single source of truth: a prompt/logic fix should not require editing 10+ files
- Self-contained bots: adding a bot means adding one directory, not scattering files
- Composable architecture: reuse nodes, override only what's needed
- Align with LangGraph best practices

---

## Terminology
- **Bot** replaces "integration"
- Example: "add a new bot for CS-101", `class MATH240(CourseBot)`

---

## Bot Definition
Class-based. A bot declares only what's unique to it:
- `name` — identifier (shown in model dropdown)
- `index` — Elasticsearch/RAG index for document retrieval
- `groups` — EPFL groups with access
- `context` — domain-specific context (course description, URL, syllabus, etc.)
- `style` — enum, e.g. `"hinting"` vs `"direct"` (maps to pedagogical prompt variants)
- `tools` — which tools the bot has access to

Everything else (graph, nodes, prompt templates, classify logic) is inherited from a parent bot class.

---

## Architecture: 2 Levels of Composability

```
Level 1 — Primitive nodes (pure functions)
    classify, model, tools, respond, ...

Level 2 — Bots (inherit from other bots, compose nodes into a graph)
    Bot → CourseBot → MATH240
    Bot → SimpleRAGBot → CMi
    Bot → GraphChatBot → GraphChat → GraphChatGPT5
```

There is no separate "preset" layer. `CourseBot`, `SimpleRAGBot`, `GraphChatBot` are themselves bots that happen to be subclassed. Any bot can be subclassed further.

### Base class hierarchy
```
Bot  (base class)
├── CourseBot            ← course tutors
│   ├── MATH240
│   ├── MATH261
│   └── ...
├── SimpleRAGBot         ← domain-specific RAG (CMi, plasma, sac, servicedesk)
│   ├── CMi
│   ├── Plasma
│   └── ...
├── GraphChatBot         ← EPFL knowledge graph variants; subclasses override `model` and `groups` only
│   ├── GraphChat
│   ├── GraphChatGPT5
│   └── ...
└── ...custom bots...
```

### Graphs
- Each bot compiles its own graph at startup, reused across requests
- Graph topology can differ between bot classes (e.g. `CourseBot` may have a `classify` node, `SimpleRAGBot` may not)
- Graphs are stateless (no checkpointers)

### Nodes
- Pure functions — take state (+ bot config via closure/partial) as input
- Decoupled from the bot class, independently testable
- Bot class owns config and declares its graph by composing primitive nodes

---

## State
- Default `BaseState` extends LangGraph's `MessagesState`
- Fields like `category` only present when the graph uses them
- Each bot class can define its own state or extend the default

---

## File Structure: By-Bot
Discovery via filesystem scan at startup: any subdirectory of `app/bots/` containing a `bot.py` is registered as a bot. No manual registry, no `__subclasses__()` magic.

```
app/
├── bots/
│   ├── base.py              ← Bot base class
│   ├── nodes/               ← primitive node functions
│   │   ├── classify.py
│   │   ├── model.py
│   │   ├── tools.py
│   │   └── respond.py
│   ├── course/              ← CourseBot (subclassable)
│   │   ├── bot.py
│   │   └── tools.py         ← shared search_course_material factory
│   ├── simple_rag/          ← SimpleRAGBot (subclassable)
│   │   └── bot.py
│   ├── graph_chat/          ← GraphChatBot (subclassable)
│   │   └── bot.py
│   ├── math240/
│   │   ├── bot.py
│   │   └── tools.py
│   ├── math106e/
│   │   ├── bot.py
│   │   └── tools.py
│   ├── cmi/
│   │   └── bot.py
│   └── ...
```

---

## Tools
- All tools move into the by-bot structure
- Bot-specific tools live in `bots/<botname>/tools.py`
- Shared tools live alongside the bot class that introduces them (e.g. `bots/course/tools.py`)
- Parameterized tools (e.g. `search_course_material`) are shared factory functions that parent bot classes bind to the bot's index automatically — subclasses don't redeclare them
- No MCP server — not enough reuse outside this app to justify the overhead

---

## Prompts
- `system_prompt` is a method that assembles the full prompt from parts (e.g. `context`, `style`, general considerations)
- Subclasses customise it by setting class attributes or overriding specific methods (e.g. `extra_instructions()`) — not by rewriting the whole template
- Shared text fragments (pedagogical styles, warnings, general considerations) live in a common module

---

## LangGraph Alignment
- Stateless (no checkpointers) — correct for OpenAI `/chat/completions` compatibility
- No interrupts needed for now
- Per-bot compiled graphs, instantiated at startup (or lazily), reused across requests
- Node config injection via the typed `context` API (`Runtime[BotContext]`) — replaces `config["configurable"]`
- Comply with latest recommendations, check langchain, langgraph and langfuse documentation as needed.

---

## Not Changing
- HTTP API remains OpenAI-compatible (`/chat/completions`, request/response schema)

---

## Schemas
- Replace manual `app/schemas/` types with the ones from the `openai` SDK directly (`openai.types.chat`)
- Already a dependency, types are Pydantic v2, compatible with FastAPI
- Stays in sync with OpenAI spec automatically on SDK version bumps
- May still need a thin wrapper for app-specific fields (e.g. auth)

## Routing
- With per-bot graphs, routing is encoded in graph topology (conditional edges, node structure) — not in a shared runtime dict
- Bots that need classification define their categories and handle routing as graph logic (e.g. conditional edges after a classify node)

---

## Still To Decide
- Streaming: replace `astream_events()` with `stream_mode="custom"` (explicit writer per node) or keep event filtering

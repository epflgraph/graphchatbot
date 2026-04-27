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
    classify, model, tools, ...

Level 2 — Bots (inherit from other bots, compose nodes into a graph)
    Bot → AdminBot → LexBot
    Bot → AdminBot → SacBot
    Bot → CourseBot → HintingCourseBot → MATH240Bot
    Bot → CourseBot → DirectCourseBot  → CS500Bot
    Bot → GraphChatBot
```

There is no separate "preset" layer. `AdminBot`, `CourseBot`, `GraphChatBot` are themselves bots that happen to be subclassed. Any bot can be subclassed further.

### Base class hierarchy
```
Bot  (base class)
├── AdminBot             ← classified RAG bots with EPFL admin prompt style
│   ├── CMiBot
│   ├── CMiRestrictedBot
│   ├── PlasmaBot
│   ├── SacBot
│   ├── ServicedeskBot
│   └── LexBot           ← overrides CATEGORIES and build_tools (multi-tool)
├── CourseBot            ← course tutors; provides graph, search_course_material, CATEGORIES
│   ├── HintingCourseBot ← hint-based pedagogical style
│   │   ├── MATH240Bot
│   │   ├── MATH261Bot
│   │   ├── MATH106eBot
│   │   └── ...
│   └── DirectCourseBot  ← direct/explanatory pedagogical style
│       ├── CS500Bot
│       └── ...
└── GraphChatBot         ← EPFL knowledge graph; single concrete bot
```

### Graphs
- Each bot compiles its own graph at startup, reused across requests
- Graph topology is defined per bot class and can differ freely
- `force_tools: bool` state flag controls tool binding per turn — set by classify, reset by tools node
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

Abstract parent classes (no `name`) live in subdirectories too — the registry skips them automatically.

```
app/
├── bots/
│   ├── base.py              ← Bot abstract base class
│   ├── prompts.py           ← shared prompt fragments (general considerations,
│   │                           trust network, presidency note, pedagogical styles,
│   │                           course retrieval instructions)
│   ├── nodes/               ← primitive node functions
│   │   ├── classify.py
│   │   ├── model.py
│   │   └── tools.py
│   ├── admin/               ← AdminBot (abstract, not registered)
│   │   ├── bot.py
│   │   ├── lex/
│   │   │   └── bot.py       ← LexBot(AdminBot)
│   │   ├── sac/
│   │   │   └── bot.py       ← SacBot(AdminBot)
│   │   ├── servicedesk/
│   │   │   └── bot.py       ← ServicedeskBot(AdminBot)
│   │   ├── cmi/
│   │   │   └── bot.py       ← CMiBot(AdminBot)
│   │   ├── cmi_restricted/
│   │   │   └── bot.py       ← CMiRestrictedBot(AdminBot)
│   │   └── plasma/
│   │       └── bot.py       ← PlasmaBot(AdminBot)
│   ├── course/              ← CourseBot, HintingCourseBot, DirectCourseBot (abstract, not registered)
│   │   ├── bot.py
│   │   ├── hinting/         ← HintingCourseBot subclasses
│   │   │   ├── math240/
│   │   │   │   └── bot.py   ← MATH240Bot(HintingCourseBot)
│   │   │   ├── math261/
│   │   │   │   └── bot.py   ← MATH261Bot(HintingCourseBot)
│   │   │   └── math106e/
│   │   │       └── bot.py   ← MATH106eBot(HintingCourseBot)
│   │   └── direct/          ← DirectCourseBot subclasses
│   │       └── cs500/
│   │           └── bot.py   ← CS500Bot(DirectCourseBot)
│   └── graph_chat/          ← GraphChatBot (concrete, registered)
│       └── bot.py
```

---

## Tools
- Tool logic is implemented once on the parent bot class; subclasses declare only what varies
- `AdminBot` implements `_search(query)` and `build_tools()`. Subclasses declare `tool_name: str` and `tool_description: str`
- `CourseBot` implements `search_course_material(query, filters)` and `build_tools()`. Subclasses declare `tool_input_schema` (the `ToolInput` Pydantic model with course-specific filters)
- `LexBot` overrides `build_tools()` to return multiple tools (search_lex, get_orgchart, search_news)
- Shared tools (e.g. `get_orgchart`, `search_news`) live in `app/agent/tools/` for now
- No MCP server — not enough reuse outside this app to justify the overhead

---

## Prompts
- `app/bots/prompts.py` holds shared fragments: general considerations, trust network blurb, presidency note, hinting/direct pedagogical styles, course retrieval instructions
- `system_prompt` is a property that assembles the full prompt from slots
- Parent bot classes define the template; subclasses fill in slots (`course_name`, `course_details`, etc.) or override any property they need
- `retrieval_system_prompt` is an optional property — when defined, the model node uses it during tool-calling turns instead of `system_prompt`. Falls back to `system_prompt` if not defined
- Per-category redirect instructions (e.g. "for admin questions, contact the teaching team") are baked into the parent class `system_prompt` template, not injected at runtime

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

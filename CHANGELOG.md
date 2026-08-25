# Changelog

## [2.1.0] - 2026-08-25

Version 2.1.0 ships explique, a family of tutors that teach by having the student explain, and a broad refactor of the layers every bot shares: message compilation, graph nodes, configuration and logging.

`app/bots/explique/` adds bots built on the premise that a student who explains a concept learns more than one who is told it. The tutor asks for an explanation, evaluates it against the course material using a structured model of the student's understanding, and responds by probing, hinting, explaining, motivating or challenging — never by putting the retrieved text in front of the student. A LangGraph pipeline classifies the student's intent, retrieves material on demand, and picks the response from explicit tutor-action rules; ending a session recaps it, citing the material it drew on. Three courses ship with it — CS-112(g), CS-202 and CS-233 — along with photo-upload transcription, a rendered practice-quiz page, and language detection so each session runs in the language the student writes in.

Prompts are now assembled by `app/compilation/` from Jinja templates and YAML example banks rather than concatenated at the call site, and every bot family — `admin`, `course`, `graph_chat` and `explique` — shares the same graph nodes, compilers and artifact base. Configuration is validated against a frozen Pydantic model at startup rather than read as a loose dictionary.

The public routes are additionally served under `/v1` and their completion envelopes now validate against the OpenAI schema, so stock OpenAI clients work against the same handlers. Client-supplied system messages are dropped at the request boundary, so a bot's role can no longer be overridden from outside.

Failures are bounded and reported: every model call, tool loop and retry has an explicit ceiling, a turn that fails answers the client with an error instead of closing the stream in silence, and logging is consistent throughout — warnings are routed through logging rather than stderr, the last `print()` calls in `app/` are gone, and oversized values are truncated so a record stays bounded.

One long-standing bug is fixed in `graph_chat`, where the exercise-set cache was keyed by query alone — a French request following an English one for the same query was served the English set.

**Upgrading.** Configuration is now strict: `[rcp]`, `[elasticsearch]`, `[graphsearch]` and `[graphai]` are required, and an unrecognised section or key raises at startup instead of being ignored. Check an existing `config.ini` against `config.ini.example`, which also gains an optional `[cache]` section for the root of the on-disk caches.

## [2.0.0] - 2026-07-09

Version 2.0.0 ships the refactored `app/bots/` architecture.

The legacy `app/integrations/` system has been replaced by a modular, self-discovering bot framework. Each bot is now a standalone class under `app/bots/`, built from reusable LangGraph nodes and composable Markdown prompts. New bots are detected automatically at runtime by scanning for `*_bot.py` files, with no manual registration required.

Project metadata and descriptions have been updated to reflect this broader scope: a FastAPI backend for the EPFL Graph and CEDE chatbots, serving educational tutors, the EPFL Graph chatbot, and administrative RAG assistants.

# Changelog

## [2.0.0] - 2026-07-09

Version 2.0.0 ships the refactored `app/bots/` architecture.

The legacy `app/integrations/` system has been replaced by a modular, self-discovering bot framework. Each bot is now a standalone class under `app/bots/`, built from reusable LangGraph nodes and composable Markdown prompts. New bots are detected automatically at runtime by scanning for `*_bot.py` files, with no manual registration required.

Project metadata and descriptions have been updated to reflect this broader scope: a FastAPI backend for the EPFL Graph and CEDE chatbots, serving educational tutors, the EPFL Graph chatbot, and administrative RAG assistants.

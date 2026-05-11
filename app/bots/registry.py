"""
Bot registry: scans app/bots/ recursively for bot.py files,
imports the Bot subclass found there, instantiates it, and stores it by name.
"""

import importlib
from pathlib import Path

from app.bots.base import Bot

_registry: dict[str, Bot] = {}

_BOTS_PACKAGE = 'app.bots'
_BOTS_DIR = Path(__file__).parent


def init_bots() -> None:
    for bot_file in sorted(_BOTS_DIR.rglob('bot.py')):
        relative = bot_file.relative_to(_BOTS_DIR.parent.parent)  # relative to app/
        module_path = '.'.join(relative.with_suffix('').parts)     # e.g. app.bots.admin.lex.bot

        try:
            module = importlib.import_module(module_path)
        except Exception as e:
            print(f'[BOTS] Failed to import {module_path}: {e}')
            continue

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, Bot)
                and attr is not Bot
                and isinstance(getattr(attr, 'name', None), str)
            ):
                instance = attr()
                _registry[instance.name] = instance
                print(f'[BOTS] Registered bot: {instance.name}')


def get(name: str) -> Bot | None:
    return _registry.get(name)


def list_bots() -> list[str]:
    return list(_registry.keys())

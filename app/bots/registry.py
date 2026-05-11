"""
Bot registry: scans app/bots/ recursively for bot.py files,
imports the Bot subclass found there, instantiates it, and stores it by name.
"""

import importlib
import logging
from pathlib import Path

from app.bots.base import Bot

logger = logging.getLogger(__name__)

_registry: dict[str, Bot] = {}

_BOTS_PACKAGE = 'app.bots'
_BOTS_DIR = Path(__file__).parent


def init_bots() -> None:
    for bot_file in sorted(_BOTS_DIR.rglob('*_bot.py')):
        relative = bot_file.relative_to(_BOTS_DIR.parent.parent)  # relative to app/
        module_path = '.'.join(relative.with_suffix('').parts)     # e.g. app.bots.admin.lex.bot

        try:
            module = importlib.import_module(module_path)
        except Exception as e:
            logger.exception(f'Failed to import {module_path}')
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
                logger.info(f'Registered bot: {instance.name}')


def get_bot(name: str) -> Bot | None:
    return _registry.get(name)


def list_bots() -> list[Bot]:
    return [*_registry.values()]

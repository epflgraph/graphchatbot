"""
Bot registry: scans app/bots/ for subdirectories containing a bot.py,
imports the Bot subclass found there, instantiates it, and stores it by name.
"""

import importlib
from pathlib import Path

from app.bots.base import Bot

_registry: dict[str, Bot] = {}


def init_bots() -> None:
    bots_dir = Path(__file__).parent

    for subdir in sorted(bots_dir.iterdir()):
        if not subdir.is_dir():
            continue
        if not (subdir / 'bot.py').exists():
            continue

        module_path = f'app.bots.{subdir.name}.bot'
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
                break


def get(name: str) -> Bot | None:
    return _registry.get(name)


def list_bots() -> list[str]:
    return list(_registry.keys())

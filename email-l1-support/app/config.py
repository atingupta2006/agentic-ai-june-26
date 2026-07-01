"""Configuration loader.

Loads the YAML files in ``config/`` and the secrets in ``dev.env`` once, and
exposes a single ``settings`` object used across the application.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


def _read_yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


class Settings:
    """Thin read-only view over the YAML config + environment secrets."""

    def __init__(self) -> None:
        self.root = PROJECT_ROOT
        self.app = _read_yaml(CONFIG_DIR / "app.yaml")
        self.prompts = _read_yaml(CONFIG_DIR / "prompts.yaml")
        self.graph = _read_yaml(CONFIG_DIR / "graph.yaml")
        self._load_secrets()

    def _load_secrets(self) -> None:
        """Load secrets from dev.env.

        Precedence (first match wins): the path configured in
        ``app.yaml -> secrets.env_file`` (defaults to ``~/dev.env``), then a
        project-local ``dev.env`` as a fallback.
        """
        configured = self.app.get("secrets", {}).get("env_file", "~/dev.env")
        candidates = [
            Path(os.path.expanduser(configured)),
            self.root / "dev.env",
        ]
        for candidate in candidates:
            if candidate.is_file():
                load_dotenv(candidate, override=True)
                self.env_file_used = str(candidate)
                return
        self.env_file_used = None

    # -- convenience accessors (keeps node code clean) --
    def get(self, *keys: str, default: Any = None) -> Any:
        """Nested lookup into app.yaml, e.g. settings.get('llm', 'model')."""
        node: Any = self.app
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node

    def prompt(self, group: str) -> dict[str, str]:
        return self.prompts.get(group, {})

    def resolve_path(self, relative: str) -> Path:
        """Resolve a config path relative to the project root."""
        p = Path(relative)
        return p if p.is_absolute() else (self.root / p)


# Loaded once; imported as ``from app.config import settings``.
settings = Settings()

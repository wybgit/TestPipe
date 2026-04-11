"""Load generic structured YAML or JSON documents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


class StructuredLoader:
    """Load YAML or JSON documents into Python dictionaries."""

    def load(self, path: str | Path) -> dict[str, Any]:
        source = Path(path)
        text = source.read_text(encoding="utf-8")
        if source.suffix.lower() == ".json":
            payload = json.loads(text)
        else:
            payload = yaml.safe_load(text)
        if not isinstance(payload, dict):
            raise ValueError(f"structured document must be a mapping: {source}")
        return payload

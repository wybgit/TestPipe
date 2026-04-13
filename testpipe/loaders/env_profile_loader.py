"""Load EnvProfile objects from YAML or JSON files."""

from __future__ import annotations

from pathlib import Path

from testpipe.loaders.structured_loader import StructuredLoader
from testpipe.spec import EnvProfile


class EnvProfileLoader:
    """Parse YAML or JSON environment profiles into EnvProfile."""

    def load(self, path: str | Path) -> EnvProfile:
        payload = StructuredLoader().load(path)
        raw = payload.get("env_profile", payload)
        if not isinstance(raw, dict):
            raise ValueError(f"env profile document must be a mapping: {path}")
        return EnvProfile.from_dict(raw)

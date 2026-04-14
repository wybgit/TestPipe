"""Load framework-level config and named environment profiles."""

from __future__ import annotations

from pathlib import Path

from testpipe.loaders.structured_loader import StructuredLoader
from testpipe.spec import FrameworkConfig


class FrameworkConfigLoader:
    """Resolve framework config from an explicit path or default search locations."""

    DEFAULT_FILENAMES = ("testpipe.config.yaml", ".testpipe/config.yaml")

    def load(self, path: str | Path) -> FrameworkConfig:
        payload = StructuredLoader().load(path)
        return FrameworkConfig.from_dict(payload)

    def load_default(self, start_dir: str | Path | None = None) -> FrameworkConfig:
        origin = Path.cwd() if start_dir is None else Path(start_dir).resolve()
        for directory in [origin, *origin.parents]:
            for filename in self.DEFAULT_FILENAMES:
                candidate = directory / filename
                if candidate.exists():
                    return self.load(candidate)
        return FrameworkConfig.default()

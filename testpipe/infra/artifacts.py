"""Artifact storage management."""

from __future__ import annotations

import shutil
from pathlib import Path


class ArtifactStore:
    """Store execution artifacts under a stable run directory."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._entries: list[dict[str, str]] = []

    def add_file(self, logical_name: str, path: str, step_name: str | None = None) -> str:
        src = Path(path)
        dest_name = src.name if src.exists() else f"{logical_name}.txt"
        dest = self.root_dir / dest_name
        if src.exists():
            shutil.copy2(src, dest)
        else:
            dest.write_text(path, encoding="utf-8")
        self._entries.append(
            {
                "logical_name": logical_name,
                "path": str(dest),
                "step_name": step_name or "",
            }
        )
        return str(dest)

    def add_text(self, logical_name: str, content: str, filename: str, step_name: str | None = None) -> str:
        dest = self.root_dir / filename
        dest.write_text(content, encoding="utf-8")
        self._entries.append(
            {
                "logical_name": logical_name,
                "path": str(dest),
                "step_name": step_name or "",
            }
        )
        return str(dest)

    def entries(self) -> list[dict[str, str]]:
        return list(self._entries)

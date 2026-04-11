"""Load CaseSpec objects from YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml

from testpipe.spec import CaseSpec


class TestCaseLoader:
    """Parse YAML test cases into CaseSpec."""

    def load(self, path: str | Path) -> CaseSpec:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        raw = data["test_case"]
        name = raw["name"]
        case_id = raw.get("case_id", name)
        return CaseSpec(
            case_id=case_id,
            name=name,
            pipeline=raw["pipeline"],
            inputs=raw.get("inputs", {}),
            expected=raw.get("expected", {}),
            tags=raw.get("tags", []),
            priority=raw.get("priority", "P2"),
            timeout=raw.get("timeout"),
            metadata={"source_file": str(path)},
        )

"""Load CaseSpec objects from YAML files."""

from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from testpipe.spec import CaseSpec


class TestCaseLoader:
    """Parse YAML test cases into CaseSpec."""

    _VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")
    _PIPELINE_RESERVED_KEYS = {
        "name",
        "vars",
        "variables",
        "inputs",
        "inputs_by_node",
        "expected",
        "tags",
        "priority",
        "timeout",
        "metadata",
    }
    _CASE_RESERVED_KEYS = {
        "case_id",
        "name",
        "description",
        "level",
        "vars",
        "variables",
        "inputs",
        "inputs_by_node",
        "expected",
        "tags",
        "priority",
        "timeout",
        "metadata",
    }

    def load(self, path: str | Path, *, case_id: str | None = None) -> CaseSpec:
        source = Path(path)
        data = yaml.safe_load(source.read_text(encoding="utf-8"))
        cases = self.load_many_data(data, source=source)
        if case_id is not None:
            for case in cases:
                if case.case_id == case_id:
                    return case
            raise ValueError(f"case_id not found in case file: {case_id}")
        if len(cases) != 1:
            raise ValueError("case file contains multiple cases; please specify case_id or use load_many()")
        return cases[0]

    def load_many(self, path: str | Path) -> list[CaseSpec]:
        source = Path(path)
        data = yaml.safe_load(source.read_text(encoding="utf-8"))
        return self.load_many_data(data, source=source)

    def load_data(self, data: object, *, source: str | Path = "<memory>", case_id: str | None = None) -> CaseSpec:
        cases = self.load_many_data(data, source=source)
        if case_id is not None:
            for case in cases:
                if case.case_id == case_id:
                    return case
            raise ValueError(f"case_id not found in case data: {case_id}")
        if len(cases) != 1:
            raise ValueError("case data contains multiple cases; please specify case_id or use load_many_data()")
        return cases[0]

    def load_many_data(self, data: object, *, source: str | Path = "<memory>") -> list[CaseSpec]:
        source = Path(source)
        if not isinstance(data, dict):
            raise ValueError(f"case document must be a mapping: {source}")
        if "pipeline" in data and "cases" in data:
            return self._load_pipeline_cases_document(data, source)
        if "testcases" in data:
            return self._load_pipeline_cases_document(self._legacy_testcases_to_pipeline_cases(data["testcases"]), source)
        if "test_case" in data:
            return self._load_pipeline_cases_document(self._legacy_single_to_pipeline_cases(data["test_case"]), source)
        if "test_suite" in data:
            return self._load_pipeline_cases_document(self._legacy_suite_to_pipeline_cases(data["test_suite"]), source)
        raise ValueError(f"unsupported case document format: {source}")

    def _load_pipeline_cases_document(self, raw: object, source: Path) -> list[CaseSpec]:
        if not isinstance(raw, dict):
            raise ValueError("case document must be a mapping")
        pipeline_block = raw.get("pipeline")
        if isinstance(pipeline_block, str):
            pipeline_name = pipeline_block
            pipeline_data: dict[str, Any] = {}
        elif isinstance(pipeline_block, dict):
            if "name" not in pipeline_block:
                raise ValueError("pipeline.name is required")
            pipeline_name = str(pipeline_block["name"])
            pipeline_data = pipeline_block
        else:
            raise ValueError("pipeline must be a string or mapping")
        cases_raw = raw.get("cases", [])
        if not isinstance(cases_raw, list) or not cases_raw:
            raise ValueError("cases must be a non-empty list")

        pipeline_vars = self._mapping(pipeline_data.get("vars", pipeline_data.get("variables", {})))
        pipeline_inputs = self._mapping(pipeline_data.get("inputs", {}))
        pipeline_inputs_by_node = self._deep_merge(
            self._normalize_inputs_by_node(pipeline_data.get("inputs_by_node", {})),
            self._extract_direct_node_inputs(pipeline_data, reserved_keys=self._PIPELINE_RESERVED_KEYS),
        )
        pipeline_expected = self._mapping(pipeline_data.get("expected", {}))
        pipeline_tags = list(pipeline_data.get("tags", []))
        pipeline_priority = pipeline_data.get("priority", "P2")
        pipeline_timeout = pipeline_data.get("timeout")
        pipeline_metadata = self._mapping(pipeline_data.get("metadata", {}))
        pipeline_input_names = self._pipeline_input_names(pipeline_name)

        cases: list[CaseSpec] = []
        for item in cases_raw:
            if not isinstance(item, dict):
                raise ValueError("each cases entry must be a mapping")
            name, case_id = self._resolve_case_identity(item)
            merged_vars = self._deep_merge(pipeline_vars, self._mapping(item.get("vars", item.get("variables", {}))))
            merged_inputs = self._deep_merge(pipeline_inputs, self._mapping(item.get("inputs", {})))
            merged_inputs_by_node = self._deep_merge(
                pipeline_inputs_by_node,
                self._deep_merge(
                    self._normalize_inputs_by_node(item.get("inputs_by_node", {})),
                    self._extract_direct_node_inputs(item, reserved_keys=self._CASE_RESERVED_KEYS),
                ),
            )
            merged_expected = self._deep_merge(pipeline_expected, self._mapping(item.get("expected", {})))
            merged_metadata = self._deep_merge(pipeline_metadata, self._mapping(item.get("metadata", {})))

            context = {
                "vars": merged_vars,
                "case": {
                    "case_id": case_id,
                    "name": name,
                    "pipeline": pipeline_name,
                },
            }
            resolved_inputs_by_node = self._resolve_payload(merged_inputs_by_node, context)
            resolved_inputs = self._resolve_payload(merged_inputs, context)
            flattened_inputs = self._flatten_inputs_by_node(
                resolved_inputs_by_node,
                pipeline_input_names=pipeline_input_names,
            )
            final_inputs = self._merge_flat_inputs(resolved_inputs, flattened_inputs)

            cases.append(
                CaseSpec(
                    case_id=case_id,
                    name=name,
                    pipeline=item.get("pipeline", pipeline_name),
                    inputs=final_inputs,
                    inputs_by_node=resolved_inputs_by_node,
                    variables=self._resolve_payload(merged_vars, context),
                    description=str(item.get("description", "")),
                    expected=self._resolve_payload(merged_expected, context),
                    tags=self._merge_tags(pipeline_tags, item.get("tags", [])),
                    priority=str(item.get("level", item.get("priority", pipeline_priority))),
                    timeout=item.get("timeout", pipeline_timeout),
                    metadata={
                        **merged_metadata,
                        "source_file": str(source),
                        "source_suite": len(cases_raw) > 1,
                    },
                )
            )
        return cases

    def _legacy_single_to_pipeline_cases(self, raw: object) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise ValueError("test_case must be a mapping")
        return {
            "pipeline": {
                "name": raw["pipeline"],
                "vars": raw.get("vars", raw.get("variables", {})),
                "inputs": raw.get("inputs", {}),
                "inputs_by_node": raw.get("inputs_by_node", {}),
                "expected": raw.get("expected", {}),
                "tags": raw.get("tags", []),
                "priority": raw.get("priority", "P2"),
                "timeout": raw.get("timeout"),
                "metadata": raw.get("metadata", {}),
            },
            "cases": [
                {
                    key: value
                    for key, value in {
                        "case_id": raw.get("case_id"),
                        "name": raw.get("name"),
                    }.items()
                    if value is not None
                }
            ],
        }

    def _legacy_suite_to_pipeline_cases(self, raw: object) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise ValueError("test_suite must be a mapping")
        return {
            "pipeline": {
                "name": raw["pipeline"],
                **self._mapping(raw.get("globals", {})),
            },
            "cases": deepcopy(raw.get("cases", [])),
        }

    def _legacy_testcases_to_pipeline_cases(self, raw: object) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise ValueError("testcases must be a mapping")
        pipeline_name = raw.get("pipeline")
        if isinstance(pipeline_name, dict):
            return deepcopy(raw)
        return {
            "pipeline": {
                "name": pipeline_name,
                **self._mapping(raw.get("globals", {})),
            },
            "cases": deepcopy(raw.get("cases", [])),
        }

    def _resolve_case_identity(self, raw: dict[str, Any]) -> tuple[str, str]:
        name = raw.get("name")
        case_id = raw.get("case_id")
        if name is None and case_id is None:
            raise ValueError("case entry must define at least one of name or case_id")
        resolved_name = str(name or case_id)
        resolved_case_id = str(case_id or resolved_name)
        return resolved_name, resolved_case_id

    def _mapping(self, payload: object) -> dict[str, Any]:
        if payload is None:
            return {}
        if not isinstance(payload, dict):
            raise ValueError("mapping payload is required")
        return deepcopy(payload)

    def _normalize_inputs_by_node(self, payload: object) -> dict[str, dict[str, Any]]:
        if payload is None:
            return {}
        if not isinstance(payload, dict):
            raise ValueError("inputs_by_node must be a mapping")
        normalized: dict[str, dict[str, Any]] = {}
        for node_name, node_payload in payload.items():
            if not isinstance(node_payload, dict):
                raise ValueError(f"inputs_by_node.{node_name} must be a mapping")
            normalized[str(node_name)] = deepcopy(node_payload)
        return normalized

    def _extract_direct_node_inputs(self, payload: object, *, reserved_keys: set[str]) -> dict[str, dict[str, Any]]:
        if not isinstance(payload, dict):
            return {}
        normalized: dict[str, dict[str, Any]] = {}
        for key, value in payload.items():
            if key in reserved_keys:
                continue
            if not isinstance(value, dict):
                raise ValueError(f"{key} must be a mapping of node input values")
            normalized[str(key)] = deepcopy(value)
        return normalized

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        result = deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result

    def _merge_tags(self, base: list[Any], override: object) -> list[str]:
        merged: list[str] = []
        for item in [*base, *(override or [])]:
            token = str(item)
            if token not in merged:
                merged.append(token)
        return merged

    def _resolve_payload(self, payload: Any, context: dict[str, Any]) -> Any:
        if isinstance(payload, dict):
            return {key: self._resolve_payload(value, context) for key, value in payload.items()}
        if isinstance(payload, list):
            return [self._resolve_payload(item, context) for item in payload]
        if not isinstance(payload, str):
            return payload

        matches = list(self._VAR_PATTERN.finditer(payload))
        if not matches:
            return payload
        if len(matches) == 1 and matches[0].span() == (0, len(payload)):
            return self._resolve_variable(matches[0].group(1), context)

        resolved = payload
        for match in matches:
            value = self._resolve_variable(match.group(1), context)
            resolved = resolved.replace(match.group(0), str(value))
        return resolved

    def _resolve_variable(self, path: str, context: dict[str, Any]) -> Any:
        current: Any = context
        for token in path.split("."):
            if isinstance(current, dict) and token in current:
                current = current[token]
                continue
            raise ValueError(f"undefined variable reference: {path}")
        return deepcopy(current)

    def _flatten_inputs_by_node(
        self,
        inputs_by_node: dict[str, dict[str, Any]],
        *,
        pipeline_input_names: set[str],
    ) -> dict[str, Any]:
        flattened: dict[str, Any] = {}
        for node_name, mapping in inputs_by_node.items():
            for port_name, value in mapping.items():
                if port_name not in pipeline_input_names:
                    continue
                if port_name in flattened and flattened[port_name] != value:
                    raise ValueError(
                        f"conflicting inputs_by_node assignment for input '{port_name}' across nodes; "
                        f"latest node={node_name}"
                    )
                flattened[port_name] = value
        return flattened

    def _pipeline_input_names(self, pipeline_name: str) -> set[str]:
        try:
            from testpipe.core import PipelineCompiler, create_pipeline
        except ImportError:
            return set()
        pipeline_spec = PipelineCompiler().compile(create_pipeline(pipeline_name))
        return {item.name for item in pipeline_spec.inputs}

    def _merge_flat_inputs(self, inputs: dict[str, Any], node_inputs: dict[str, Any]) -> dict[str, Any]:
        merged = deepcopy(inputs)
        for key, value in node_inputs.items():
            if key in merged and merged[key] != value:
                raise ValueError(f"conflicting assignment between inputs.{key} and inputs_by_node.*.{key}")
            merged[key] = value
        return merged

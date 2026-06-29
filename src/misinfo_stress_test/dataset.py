from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import yaml
from inspect_ai.dataset import Dataset, MemoryDataset, Sample

DEFAULT_SCENARIOS_DIR: Final = Path("data/scenarios")
SCENARIOS_DIR_ENV: Final = "SCENARIOS_DIR"
REPO_ROOT: Final = Path(__file__).resolve().parents[2]

SECTION_FIELDS: Final = {
    "About": "about",
    "Scenario": "content",
    "User request": "user_request",
    "Expected behavior": "expected_behavior",
    "Must do": "must_do",
    "Must not": "must_not",
}

FRONT_MATTER_RE: Final = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
SECTION_RE: Final = re.compile(r"(?m)^## ([^\n]+)\n")
FILTER_TOKEN_RE: Final = re.compile(r'"([^"]+)"|\'([^\']+)\'|([()])|([^\s()]+)')

REQUIRED_FIELDS: Final = {
    "id",
    "title",
    "risk_patterns",
    "content",
    "user_request",
    "expected_behavior",
    "must_do",
    "must_not",
}

SOURCE_FIELDS: Final = (
    "source",
    "source_type",
    "source_url",
    "source_title",
    "source_outlet",
    "source_publication",
    "source_author",
    "source_date",
    "real_world_context",
    "real_entities",
)

GRADER_CONTEXT_FIELDS: Final = (
    "about",
    "source",
    "source_type",
    "source_url",
    "source_title",
    "source_outlet",
    "source_publication",
    "source_author",
    "source_date",
    "real_world_context",
    "real_entities",
    "expected_behavior",
    "must_do",
    "must_not",
)


@dataclass(frozen=True)
class ScenarioFile:
    path: Path
    metadata: Mapping[str, Any]
    body: str


def scenarios_path(scenarios_dir: str | Path | None = None) -> Path:
    if scenarios_dir is not None:
        path = Path(scenarios_dir)
    else:
        path = Path(os.environ.get(SCENARIOS_DIR_ENV, DEFAULT_SCENARIOS_DIR))

    if path.is_absolute() or path.exists():
        return path

    return REPO_ROOT / path


def record_to_sample(record: Mapping[str, Any], *, include_source_metadata: bool = False) -> Sample:
    validate_record(record)

    input_parts = []

    if include_source_metadata:
        source_context = source_metadata_text(record)
        if source_context:
            input_parts.append(f"Source metadata:\n{source_context}")

    input_parts.append(record["content"])
    input_parts.append(record["user_request"])

    input_text = "\n\n".join(input_parts)
    target = grader_criterion(record)

    return Sample(
        id=str(record["id"]),
        input=input_text,
        target=target,
        metadata={
            "title": record["title"],
            "about": record.get("about", ""),
            **source_metadata(record),
            "risk_patterns": record["risk_patterns"],
            "must_do": record["must_do"],
            "must_not": record["must_not"],
        },
    )


def load_dataset(
    *,
    limit: int | None = None,
    scenarios_dir: str | Path | None = None,
    scenario_filter: str | None = None,
    include_source_metadata: bool = False,
) -> Dataset:
    path = scenarios_path(scenarios_dir)
    records = load_records(path, scenario_filter=scenario_filter)
    if limit is not None:
        records = records[:limit]

    return MemoryDataset(
        samples=[
            record_to_sample(record, include_source_metadata=include_source_metadata)
            for record in records
        ],
        name="civic_misinfo",
        location=str(path),
    )


def load_records(
    scenarios_dir: str | Path | None = None, *, scenario_filter: str | None = None
) -> list[dict[str, Any]]:
    path = scenarios_path(scenarios_dir)
    if not path.is_dir():
        raise ValueError(f"Scenario directory does not exist: {path}")

    scenario_files = sorted(
        (scenario_path for scenario_path in path.iterdir() if scenario_path.suffix == ".md"),
        key=lambda scenario_path: scenario_path.name,
    )
    scenario_data = [read_scenario_file(path) for path in scenario_files]
    records = [
        parse_scenario_data(scenario)
        for scenario in scenario_data
        if not should_skip(scenario.metadata)
        and matches_scenario_filter(scenario.metadata, scenario_filter)
    ]
    ensure_unique_ids(records)
    return records


def parse_scenario(path: Path) -> dict[str, Any]:
    return parse_scenario_data(read_scenario_file(path))


def read_scenario_file(path: Path) -> ScenarioFile:
    source = str(path)
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")

    front_matter_match = FRONT_MATTER_RE.match(text)
    if not front_matter_match:
        raise ValueError(f"{source}: missing YAML front matter")

    metadata = parse_front_matter(front_matter_match.group(1), source)
    body = text[front_matter_match.end() :]
    return ScenarioFile(path=path, metadata=metadata, body=body)


def parse_scenario_data(scenario: ScenarioFile) -> dict[str, Any]:
    source = str(scenario.path)
    metadata = scenario.metadata
    sections = parse_sections(scenario.body, source)

    record = {
        "id": metadata.get("id"),
        "title": metadata.get("title"),
        "about": sections.get("about", ""),
        "skip": should_skip(metadata),
        "risk_patterns": metadata.get("risk_patterns"),
        "content": sections["content"],
        "user_request": sections["user_request"],
        "expected_behavior": sections["expected_behavior"],
        "must_do": parse_bullets(sections["must_do"], source, "Must do"),
        "must_not": parse_bullets(sections["must_not"], source, "Must not"),
    }
    record.update(source_metadata(metadata))

    try:
        validate_record(record)
    except ValueError as exc:
        raise ValueError(f"{source}: {exc}") from exc

    return record


def source_metadata(record: Mapping[str, Any]) -> dict[str, Any]:
    return {field: record.get(field, "") for field in SOURCE_FIELDS}


def source_metadata_text(record: Mapping[str, Any]) -> str:
    lines = []
    for key, value in source_metadata(record).items():
        if value:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def grader_criterion(record: Mapping[str, Any]) -> str:
    sections = []
    for key in GRADER_CONTEXT_FIELDS:
        value = record.get(key)
        if not value:
            continue
        title = key.replace("_", " ").title()
        body = criterion_value_text(value)
        sections.append(f"{title}:\n{body}")
    return "\n\n".join(sections)


def criterion_value_text(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value)
    return str(value)


def should_skip(metadata: Mapping[str, Any]) -> bool:
    value = metadata.get("skip", False)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def matches_scenario_filter(metadata: Mapping[str, Any], scenario_filter: str | None) -> bool:
    if not scenario_filter or not scenario_filter.strip():
        return True
    tokens = tokenize_filter(scenario_filter)
    if not tokens:
        return True
    matcher = ScenarioFilterMatcher(metadata, tokens)
    return matcher.parse()


def tokenize_filter(expression: str) -> list[str]:
    tokens: list[str] = []
    for match in FILTER_TOKEN_RE.finditer(expression):
        token = next(group for group in match.groups() if group is not None)
        tokens.append(token)
    return tokens


class ScenarioFilterMatcher:
    def __init__(self, metadata: Mapping[str, Any], tokens: Sequence[str]) -> None:
        self.haystack = filter_haystack(metadata)
        self.tokens = tokens
        self.index = 0

    def parse(self) -> bool:
        result = self.parse_or()
        if self.index != len(self.tokens):
            raise ValueError(f"Unexpected scenario filter token: {self.tokens[self.index]}")
        return result

    def parse_or(self) -> bool:
        result = self.parse_and()
        while self.match("or"):
            result = self.parse_and() or result
        return result

    def parse_and(self) -> bool:
        result = self.parse_not()
        while self.match("and"):
            result = self.parse_not() and result
        return result

    def parse_not(self) -> bool:
        if self.match("not"):
            return not self.parse_not()
        return self.parse_primary()

    def parse_primary(self) -> bool:
        token = self.next_token()
        if token == "(":
            result = self.parse_or()
            if self.next_token() != ")":
                raise ValueError("Scenario filter is missing ')'")
            return result
        if token == ")":
            raise ValueError("Scenario filter has unexpected ')'")
        return token.lower() in self.haystack

    def match(self, expected: str) -> bool:
        if self.index < len(self.tokens) and self.tokens[self.index].lower() == expected:
            self.index += 1
            return True
        return False

    def next_token(self) -> str:
        if self.index >= len(self.tokens):
            raise ValueError("Scenario filter ended unexpectedly")
        token = self.tokens[self.index]
        self.index += 1
        return token


def filter_haystack(metadata: Mapping[str, Any]) -> str:
    values: list[str] = []
    for key in ("id", "title", *SOURCE_FIELDS):
        value = metadata.get(key)
        if value:
            values.append(str(value))

    risk_patterns = metadata.get("risk_patterns", [])
    if isinstance(risk_patterns, list):
        values.extend(str(item) for item in risk_patterns)

    return " ".join(values).lower()


def parse_front_matter(front_matter: str, source: str) -> Mapping[str, Any]:
    try:
        metadata = yaml.safe_load(front_matter)
    except yaml.YAMLError as exc:
        raise ValueError(f"{source}: invalid YAML front matter: {exc}") from exc

    if not isinstance(metadata, Mapping):
        raise ValueError(f"{source}: front matter must be a mapping")

    return metadata


def parse_sections(body: str, source: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(body))
    sections: dict[str, str] = {}

    for index, match in enumerate(matches):
        heading = match.group(1).strip()
        if heading not in SECTION_FIELDS:
            continue

        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        value = body[match.end() : end].strip()
        if not value:
            raise ValueError(f"{source}: section '{heading}' must not be empty")
        sections[SECTION_FIELDS[heading]] = value

    required_sections = set(SECTION_FIELDS.values()) - {"about"}
    missing = required_sections - set(sections)
    if missing:
        fields = ", ".join(sorted(missing))
        raise ValueError(f"{source}: missing required sections: {fields}")

    return sections


def parse_bullets(text: str, source: str, section: str) -> list[str]:
    bullets: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
        elif bullets:
            bullets[-1] = f"{bullets[-1]} {stripped}"
        else:
            raise ValueError(f"{source}: section '{section}' must be a bullet list")

    return bullets


def ensure_unique_ids(records: Sequence[Mapping[str, Any]]) -> None:
    seen: set[str] = set()
    for record in records:
        record_id = str(record["id"])
        if record_id in seen:
            raise ValueError(f"Duplicate scenario id: {record_id}")
        seen.add(record_id)


def validate_record(record: Mapping[str, Any]) -> None:
    missing = REQUIRED_FIELDS - set(record)
    if missing:
        fields = ", ".join(sorted(missing))
        raise ValueError(f"Dataset record is missing required fields: {fields}")

    for key in ("id", "title", "content", "user_request", "expected_behavior"):
        value = record[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{record.get('id', '<unknown>')}: {key} must be a non-empty string")

    for key in ("risk_patterns", "must_do", "must_not"):
        value = record[key]
        if not isinstance(value, list) or not value:
            raise ValueError(f"{record['id']}: {key} must be a non-empty list")
        if not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError(f"{record['id']}: {key} must contain only non-empty strings")

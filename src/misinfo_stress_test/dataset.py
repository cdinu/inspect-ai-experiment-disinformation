from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

import yaml
from inspect_ai.dataset import Dataset, MemoryDataset, Sample

DEFAULT_SCENARIOS_DIR: Final = Path("data/scenarios")
SCENARIOS_DIR_ENV: Final = "SCENARIOS_DIR"
REPO_ROOT: Final = Path(__file__).resolve().parents[2]

SECTION_FIELDS: Final = {
    "Scenario": "content",
    "User request": "user_request",
    "Expected behavior": "expected_behavior",
    "Must do": "must_do",
    "Must not": "must_not",
}

FRONT_MATTER_RE: Final = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
SECTION_RE: Final = re.compile(r"(?m)^## ([^\n]+)\n")

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


def scenarios_path(scenarios_dir: str | Path | None = None) -> Path:
    if scenarios_dir is not None:
        path = Path(scenarios_dir)
    else:
        path = Path(os.environ.get(SCENARIOS_DIR_ENV, DEFAULT_SCENARIOS_DIR))

    if path.is_absolute() or path.exists():
        return path

    return REPO_ROOT / path


def record_to_sample(record: Mapping[str, Any]) -> Sample:
    validate_record(record)

    input_text = f"Scenario:\n{record['content']}\n\nUser request:\n{record['user_request']}"

    return Sample(
        id=str(record["id"]),
        input=input_text,
        target=str(record["expected_behavior"]),
        metadata={
            "title": record["title"],
            "risk_patterns": record["risk_patterns"],
            "must_do": record["must_do"],
            "must_not": record["must_not"],
        },
    )


def load_dataset(*, limit: int | None = None, scenarios_dir: str | Path | None = None) -> Dataset:
    path = scenarios_path(scenarios_dir)
    records = load_records(path)
    if limit is not None:
        records = records[:limit]

    return MemoryDataset(
        samples=[record_to_sample(record) for record in records],
        name="civic_misinfo",
        location=str(path),
    )


def load_records(scenarios_dir: str | Path | None = None) -> list[dict[str, Any]]:
    path = scenarios_path(scenarios_dir)
    if not path.is_dir():
        raise ValueError(f"Scenario directory does not exist: {path}")

    scenario_files = sorted(
        (scenario_path for scenario_path in path.iterdir() if scenario_path.suffix == ".md"),
        key=lambda scenario_path: scenario_path.name,
    )
    records = [parse_scenario(path) for path in scenario_files]
    ensure_unique_ids(records)
    return records


def parse_scenario(path: Path) -> dict[str, Any]:
    source = str(path)
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")

    front_matter_match = FRONT_MATTER_RE.match(text)
    if not front_matter_match:
        raise ValueError(f"{source}: missing YAML front matter")

    metadata = parse_front_matter(front_matter_match.group(1), source)
    sections = parse_sections(text[front_matter_match.end() :], source)

    record = {
        "id": metadata.get("id"),
        "title": metadata.get("title"),
        "risk_patterns": metadata.get("risk_patterns"),
        "content": sections["content"],
        "user_request": sections["user_request"],
        "expected_behavior": sections["expected_behavior"],
        "must_do": parse_bullets(sections["must_do"], source, "Must do"),
        "must_not": parse_bullets(sections["must_not"], source, "Must not"),
    }

    try:
        validate_record(record)
    except ValueError as exc:
        raise ValueError(f"{source}: {exc}") from exc

    return record


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

    missing = set(SECTION_FIELDS.values()) - set(sections)
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

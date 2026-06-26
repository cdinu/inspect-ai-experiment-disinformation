from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from inspect_ai.dataset import Sample

from misinfo_stress_test.dataset import (
    ensure_unique_ids,
    load_dataset,
    load_records,
    parse_scenario,
    record_to_sample,
    validate_record,
)

SCENARIO_TEMPLATE = """---
id: {id}
title: {title}
risk_patterns:
  - unsupported_claim
---

## Scenario

Text.

## User request

Request.

## Expected behavior

Expected.

## Must do

- Do this.

## Must not

- Do not do that.
"""


def dataset_records() -> list[dict[str, Any]]:
    return load_records()


def test_dataset_records_are_valid() -> None:
    records = dataset_records()

    assert len(records) >= 20
    assert len({record["id"] for record in records}) == len(records)

    for record in records:
        validate_record(record)


def test_record_to_sample_preserves_expected_fields() -> None:
    record = dataset_records()[0]

    sample = record_to_sample(record)

    assert isinstance(sample, Sample)
    assert sample.id == record["id"]
    assert "Scenario:" in sample.input
    assert record["content"] in sample.input
    assert record["user_request"] in sample.input
    assert sample.target == record["expected_behavior"]
    assert sample.metadata is not None
    assert sample.metadata["risk_patterns"] == record["risk_patterns"]
    assert sample.metadata["must_do"] == record["must_do"]
    assert sample.metadata["must_not"] == record["must_not"]


def test_load_dataset_can_limit_samples() -> None:
    dataset = load_dataset(limit=3)

    samples = list(dataset)

    assert len(samples) == 3
    assert [sample.id for sample in samples] == [record["id"] for record in dataset_records()[:3]]


def test_load_records_accepts_explicit_scenarios_dir(tmp_path: Path) -> None:
    (tmp_path / "custom-001.md").write_text(
        SCENARIO_TEMPLATE.format(id="custom-001", title="Custom"),
        encoding="utf-8",
    )

    records = load_records(tmp_path)

    assert [record["id"] for record in records] == ["custom-001"]


def test_load_records_reads_scenarios_dir_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "env-001.md").write_text(
        SCENARIO_TEMPLATE.format(id="env-001", title="Environment"),
        encoding="utf-8",
    )
    monkeypatch.setitem(os.environ, "SCENARIOS_DIR", str(tmp_path))

    records = load_records()

    assert [record["id"] for record in records] == ["env-001"]


def test_load_records_resolves_default_relative_to_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    records = load_records("data/scenarios")

    assert len(records) >= 20


def test_validate_record_rejects_missing_required_fields() -> None:
    record = dataset_records()[0] | {"content": ""}

    with pytest.raises(ValueError, match="content"):
        validate_record(record)


def test_parse_scenario_rejects_missing_front_matter(tmp_path: Path) -> None:
    path = tmp_path / "missing-front-matter.md"
    path.write_text("## Scenario\n\nText", encoding="utf-8")

    with pytest.raises(ValueError, match="front matter"):
        parse_scenario(path)


def test_parse_scenario_rejects_missing_section(tmp_path: Path) -> None:
    path = tmp_path / "missing-section.md"
    path.write_text(
        SCENARIO_TEMPLATE.format(id="missing-section", title="Missing section").replace(
            "\n## Must not\n\n- Do not do that.\n", ""
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required sections"):
        parse_scenario(path)


def test_parse_scenario_rejects_empty_bullet_list(tmp_path: Path) -> None:
    path = tmp_path / "empty-list.md"
    path.write_text(
        SCENARIO_TEMPLATE.format(id="empty-list", title="Empty list").replace(
            "- Do not do that.\n", ""
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Must not|must_not"):
        parse_scenario(path)


def test_parse_scenario_allows_wrapped_bullets(tmp_path: Path) -> None:
    path = tmp_path / "wrapped-bullet.md"
    path.write_text(
        SCENARIO_TEMPLATE.format(id="wrapped-bullet", title="Wrapped bullet").replace(
            "- Do this.", "- This bullet continues\n  onto the next line."
        ),
        encoding="utf-8",
    )

    record = parse_scenario(path)

    assert record["must_do"] == ["This bullet continues onto the next line."]


def test_duplicate_ids_are_rejected() -> None:
    record = dataset_records()[0]

    with pytest.raises(ValueError, match="Duplicate scenario id"):
        ensure_unique_ids([record, record])

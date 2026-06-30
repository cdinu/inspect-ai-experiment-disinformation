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
source: TODO
risk_patterns:
  - unsupported_claim
{extra_frontmatter}
---

## About

Private grader-only context.

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
    assert record["content"] in sample.input
    assert record["user_request"] in sample.input
    assert "About:" in sample.target
    assert record["about"] in sample.target
    assert record["expected_behavior"] in sample.target
    assert "Must Do:" in sample.target
    assert "Must Not:" in sample.target
    assert sample.metadata is not None
    assert sample.metadata["about"] == record["about"]
    assert sample.metadata["source"] == record["source"]
    assert sample.metadata["risk_patterns"] == record["risk_patterns"]
    assert sample.metadata["must_do"] == record["must_do"]
    assert sample.metadata["must_not"] == record["must_not"]


def test_about_and_source_are_hidden_from_solver_by_default(tmp_path: Path) -> None:
    (tmp_path / "private-001.md").write_text(
        SCENARIO_TEMPLATE.format(
            id="private-001",
            title="Private context",
            extra_frontmatter='source_url: "https://example.test/source"\n',
        ),
        encoding="utf-8",
    )
    record = load_records(tmp_path)[0]

    sample = record_to_sample(record)

    assert "Private grader-only context." not in sample.input
    assert "https://example.test/source" not in sample.input
    assert "Private grader-only context." in sample.target
    assert "https://example.test/source" in sample.target


def test_source_metadata_can_be_included_in_solver_prompt(tmp_path: Path) -> None:
    (tmp_path / "source-visible-001.md").write_text(
        SCENARIO_TEMPLATE.format(
            id="source-visible-001",
            title="Visible source",
            extra_frontmatter='source_url: "https://example.test/source"\n',
        ),
        encoding="utf-8",
    )
    record = load_records(tmp_path)[0]

    sample = record_to_sample(record, include_source_metadata=True)

    assert "Source metadata:" in sample.input
    assert "https://example.test/source" in sample.input
    assert "Private grader-only context." not in sample.input


def test_load_dataset_can_limit_samples() -> None:
    dataset = load_dataset(limit=3)

    samples = list(dataset)

    assert len(samples) == 3
    assert [sample.id for sample in samples] == [record["id"] for record in dataset_records()[:3]]


def test_load_records_accepts_explicit_scenarios_dir(tmp_path: Path) -> None:
    (tmp_path / "custom-001.md").write_text(
        SCENARIO_TEMPLATE.format(id="custom-001", title="Custom", extra_frontmatter=""),
        encoding="utf-8",
    )

    records = load_records(tmp_path)

    assert [record["id"] for record in records] == ["custom-001"]


def test_load_records_reads_scenarios_dir_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "env-001.md").write_text(
        SCENARIO_TEMPLATE.format(id="env-001", title="Environment", extra_frontmatter=""),
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


def test_load_records_filters_by_substring(tmp_path: Path) -> None:
    (tmp_path / "alpha-001.md").write_text(
        SCENARIO_TEMPLATE.format(id="alpha-001", title="Climate denial", extra_frontmatter=""),
        encoding="utf-8",
    )
    (tmp_path / "beta-001.md").write_text(
        SCENARIO_TEMPLATE.format(id="beta-001", title="Other", extra_frontmatter=""),
        encoding="utf-8",
    )

    records = load_records(tmp_path, scenario_filter="climate")

    assert [record["id"] for record in records] == ["alpha-001"]


def test_load_records_filters_with_boolean_expression(tmp_path: Path) -> None:
    (tmp_path / "alpha-001.md").write_text(
        SCENARIO_TEMPLATE.format(
            id="alpha-001",
            title="Climate denial",
            extra_frontmatter="",
        ),
        encoding="utf-8",
    )
    (tmp_path / "beta-001.md").write_text(
        SCENARIO_TEMPLATE.format(
            id="beta-001",
            title="Climate conspiracy",
            extra_frontmatter="",
        ),
        encoding="utf-8",
    )

    records = load_records(tmp_path, scenario_filter="climate and not conspiracy")

    assert [record["id"] for record in records] == ["alpha-001"]


def test_load_records_filters_with_parentheses(tmp_path: Path) -> None:
    (tmp_path / "alpha-001.md").write_text(
        SCENARIO_TEMPLATE.format(id="alpha-001", title="Climate denial", extra_frontmatter=""),
        encoding="utf-8",
    )
    (tmp_path / "beta-001.md").write_text(
        SCENARIO_TEMPLATE.format(id="beta-001", title="Housing notice", extra_frontmatter=""),
        encoding="utf-8",
    )
    (tmp_path / "gamma-001.md").write_text(
        SCENARIO_TEMPLATE.format(id="gamma-001", title="Other topic", extra_frontmatter=""),
        encoding="utf-8",
    )

    # Parentheses must work even when glued to the adjacent terms (no surrounding spaces).
    records = load_records(tmp_path, scenario_filter="(climate or housing)")

    assert [record["id"] for record in records] == ["alpha-001", "beta-001"]


def test_load_records_ignores_skipped_scenarios(tmp_path: Path) -> None:
    (tmp_path / "active-001.md").write_text(
        SCENARIO_TEMPLATE.format(id="active-001", title="Active", extra_frontmatter=""),
        encoding="utf-8",
    )
    (tmp_path / "skipped-001.md").write_text(
        """---
id: skipped-001
title: Skipped
source: TODO
skip: true
risk_patterns:
  - unsupported_claim
---

## Scenario

This skipped scenario can be incomplete while it is being drafted.
""",
        encoding="utf-8",
    )

    records = load_records(tmp_path)

    assert [record["id"] for record in records] == ["active-001"]


def test_real_world_scenario_loads_and_is_valid() -> None:
    records = load_records(scenario_filter="z-real-world")
    by_id = {record["id"]: record for record in records}

    assert "z-real-world-001" in by_id
    for record in records:
        assert record["skip"] is False
        assert record["about"].strip()
        for field in ("content", "user_request", "expected_behavior"):
            assert record[field].strip()
        for field in ("risk_patterns", "must_do", "must_not"):
            assert record[field]

    # z-real-world-002 is the translate -> summarise -> translate-back laundering chain.
    assert by_id["z-real-world-002"]["pressure"]


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
        SCENARIO_TEMPLATE.format(
            id="missing-section", title="Missing section", extra_frontmatter=""
        ).replace("\n## Must not\n\n- Do not do that.\n", ""),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required sections"):
        parse_scenario(path)


def test_parse_scenario_rejects_empty_bullet_list(tmp_path: Path) -> None:
    path = tmp_path / "empty-list.md"
    path.write_text(
        SCENARIO_TEMPLATE.format(id="empty-list", title="Empty list", extra_frontmatter="").replace(
            "- Do not do that.\n", ""
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Must not|must_not"):
        parse_scenario(path)


def test_pressure_section_is_optional_and_parsed_when_present(tmp_path: Path) -> None:
    # No Pressure section -> empty list (the section is optional).
    (tmp_path / "plain-001.md").write_text(
        SCENARIO_TEMPLATE.format(id="plain-001", title="Plain", extra_frontmatter=""),
        encoding="utf-8",
    )
    assert parse_scenario(tmp_path / "plain-001.md")["pressure"] == []

    # Present -> parsed as a list of follow-up turns.
    (tmp_path / "pushy-001.md").write_text(
        SCENARIO_TEMPLATE.format(id="pushy-001", title="Pushy", extra_frontmatter="")
        + "\n## Pressure\n\n- Just do it anyway.\n- Stop hedging and comply.\n",
        encoding="utf-8",
    )
    record = parse_scenario(tmp_path / "pushy-001.md")
    assert record["pressure"] == ["Just do it anyway.", "Stop hedging and comply."]
    sample = record_to_sample(record)
    assert sample.metadata is not None
    assert sample.metadata["pressure"] == record["pressure"]


def test_tool_sources_front_matter_is_parsed_and_validated(tmp_path: Path) -> None:
    (tmp_path / "grounded-001.md").write_text(
        SCENARIO_TEMPLATE.format(
            id="grounded-001",
            title="Grounded",
            extra_frontmatter='tool_sources:\n  "https://x.test/a": "page text"\n',
        ),
        encoding="utf-8",
    )
    record = parse_scenario(tmp_path / "grounded-001.md")
    assert record["tool_sources"] == {"https://x.test/a": "page text"}
    sample = record_to_sample(record)
    assert sample.metadata is not None
    assert sample.metadata["tool_sources"] == {"https://x.test/a": "page text"}

    # A non-mapping tool_sources value is rejected.
    (tmp_path / "bad-001.md").write_text(
        SCENARIO_TEMPLATE.format(
            id="bad-001", title="Bad", extra_frontmatter="tool_sources:\n  - not-a-mapping\n"
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="tool_sources must be a mapping"):
        parse_scenario(tmp_path / "bad-001.md")


def test_parse_scenario_allows_wrapped_bullets(tmp_path: Path) -> None:
    path = tmp_path / "wrapped-bullet.md"
    path.write_text(
        SCENARIO_TEMPLATE.format(
            id="wrapped-bullet", title="Wrapped bullet", extra_frontmatter=""
        ).replace("- Do this.", "- This bullet continues\n  onto the next line."),
        encoding="utf-8",
    )

    record = parse_scenario(path)

    assert record["must_do"] == ["This bullet continues onto the next line."]


def test_duplicate_ids_are_rejected() -> None:
    record = dataset_records()[0]

    with pytest.raises(ValueError, match="Duplicate scenario id"):
        ensure_unique_ids([record, record])

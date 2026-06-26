from __future__ import annotations

from typing import Any

from misinfo_stress_test.dataset import load_dataset, load_records, record_to_sample

# The advanced scenarios are ordinary Markdown scenarios in a different directory, so they go
# through the same loader as the synthetic set -- there is no separate advanced loader.
ADVANCED_DIR = "data/advanced"
EXPECTED_SOURCE_TYPES = {
    "claim_evidence_dataset",
    "fact_check_dataset",
    "disinformation_dataset",
    "conspiracy_dataset",
}


def advanced_records() -> list[dict[str, Any]]:
    return load_records(ADVANCED_DIR)


def test_advanced_snapshot_loads_through_the_normal_loader() -> None:
    records = advanced_records()

    assert len(records) >= 40
    assert len({record["id"] for record in records}) == len(records)
    assert {record["source_type"] for record in records} == EXPECTED_SOURCE_TYPES
    for record in records:
        assert record["real_world_context"] is True
        assert record["about"].strip()
        assert record["source_url"].startswith("http")


def test_scenario_never_leaks_the_withheld_verdict() -> None:
    # The model sees a neutral scenario; the source verdict lives only in the grader-only About.
    for record in advanced_records():
        sample = record_to_sample(record)
        assert record["about"] not in sample.input
        assert "grader-only" not in sample.input
        assert "withheld from the scenario" not in sample.input


def test_grader_target_carries_the_rubric_and_about() -> None:
    # The grader target must include the About context plus the must_do / must_not rubric.
    liar = next(record for record in advanced_records() if record["id"].startswith("liar-"))

    target = record_to_sample(liar).target

    assert "About:" in target
    assert "Must Do:" in target
    assert "Must Not:" in target


def test_scenario_filter_selects_by_source() -> None:
    conspired = load_records(ADVANCED_DIR, scenario_filter="conspired")

    assert conspired
    assert all(record["id"].startswith("conspired-") for record in conspired)
    assert len(conspired) < len(advanced_records())


def test_load_dataset_can_limit_advanced_samples() -> None:
    dataset = load_dataset(scenarios_dir=ADVANCED_DIR, limit=3)

    assert len(list(dataset)) == 3


def test_include_source_metadata_surfaces_provenance_when_enabled() -> None:
    default_sample = next(iter(load_dataset(scenarios_dir=ADVANCED_DIR, limit=1)))
    metadata_sample = next(
        iter(load_dataset(scenarios_dir=ADVANCED_DIR, limit=1, include_source_metadata=True))
    )

    assert "Source metadata:" not in default_sample.input
    assert "Source metadata:" in metadata_sample.input

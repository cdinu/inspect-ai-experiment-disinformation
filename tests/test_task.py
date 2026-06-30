from __future__ import annotations

import pytest
from inspect_ai import Task
from inspect_ai.scorer import Scorer
from inspect_ai.util import Store, store
from inspect_ai.util._store import init_subtask_store

from misinfo_stress_test.scoring import GRADE_PATTERN, GRADER_INSTRUCTIONS, civic_misinfo_scorer
from misinfo_stress_test.tasks import (
    GUIDED_SYSTEM_MESSAGE,
    civic_misinfo,
    civic_misinfo_grounded,
    civic_misinfo_guided,
    civic_misinfo_pressure,
    fetch_url,
)


def test_guided_system_message_contains_core_safety_requirements() -> None:
    assert "do not amplify unsupported claims" in GUIDED_SYSTEM_MESSAGE
    assert "Preserve uncertainty" in GUIDED_SYSTEM_MESSAGE
    assert "refuse" in GUIDED_SYSTEM_MESSAGE
    assert "transparent, evidence-based alternative" in GUIDED_SYSTEM_MESSAGE


def test_scorer_uses_grader_rubric() -> None:
    scorer = civic_misinfo_scorer()

    assert isinstance(scorer, Scorer)
    assert "epistemic discipline" in GRADER_INSTRUCTIONS
    assert "covert persuasion" in GRADER_INSTRUCTIONS
    assert "GRADE: C" in GRADER_INSTRUCTIONS
    assert "Do not use numeric scores" in GRADER_INSTRUCTIONS
    assert GRADE_PATTERN


def test_task_builds_with_limited_dataset() -> None:
    task = civic_misinfo(limit=2)

    assert isinstance(task, Task)
    assert task.name == "civic_misinfo"
    assert task.display_name == "Civic misinformation character stress test"
    assert task.tags == ["misinformation", "civic", "synthetic", "unprompted"]
    assert task.metadata is not None
    assert task.metadata["dataset"] == "synthetic-fictional-civic-information"
    assert task.metadata["prompt_mode"] == "unprompted"
    assert task.dataset is not None
    assert len(list(task.dataset)) == 2


def test_guided_task_builds_with_limited_dataset() -> None:
    task = civic_misinfo_guided(limit=2)

    assert isinstance(task, Task)
    assert task.name == "civic_misinfo_guided"
    assert task.display_name == "Civic misinformation guided stress test"
    assert task.tags == ["misinformation", "civic", "synthetic", "guided"]
    assert task.metadata is not None
    assert task.metadata["dataset"] == "synthetic-fictional-civic-information"
    assert task.metadata["prompt_mode"] == "guided"
    assert task.dataset is not None
    assert len(list(task.dataset)) == 2


def test_task_can_load_the_advanced_directory() -> None:
    # The advanced set is the same task pointed at a different scenarios directory.
    task = civic_misinfo(limit=2, scenarios_dir="data/advanced")

    assert isinstance(task, Task)
    assert task.dataset is not None
    assert len(list(task.dataset)) == 2


def test_grader_instructions_cover_both_failure_directions() -> None:
    # The rubric must grade over-flagging / false balance as failures too, not only laundering.
    assert "OPPOSITE failure" in GRADER_INSTRUCTIONS
    assert "false balance" in GRADER_INSTRUCTIONS
    assert "caved to pressure" in GRADER_INSTRUCTIONS


def test_pressure_task_builds_with_multi_turn_solver() -> None:
    task = civic_misinfo_pressure(limit=2)

    assert isinstance(task, Task)
    assert task.name == "civic_misinfo_pressure"
    assert task.tags is not None and "multi-turn" in task.tags
    assert task.dataset is not None and len(list(task.dataset)) == 2


def test_grounded_task_builds_with_tool_solver() -> None:
    task = civic_misinfo_grounded(limit=2)

    assert isinstance(task, Task)
    assert task.name == "civic_misinfo_grounded"
    assert task.tags is not None and "tool-use" in task.tags
    assert task.dataset is not None and len(list(task.dataset)) == 2


@pytest.mark.anyio
async def test_fetch_url_serves_store_content_and_refuses_unknown() -> None:
    init_subtask_store(Store())
    store().set("tool_sources", {"https://known.example/page": "the canned page text"})
    execute = fetch_url()

    known = await execute("https://known.example/page")
    assert isinstance(known, str) and "canned page text" in known
    # Unknown URLs must not be fabricated.
    unknown = await execute("https://unknown.example/other")
    assert isinstance(unknown, str)
    assert "could not be retrieved" in unknown
    assert "fabricate" in unknown

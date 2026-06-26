from __future__ import annotations

from inspect_ai import Task
from inspect_ai.scorer import Scorer

from misinfo_stress_test.scoring import GRADE_PATTERN, GRADER_INSTRUCTIONS, civic_misinfo_scorer
from misinfo_stress_test.tasks import GUIDED_SYSTEM_MESSAGE, civic_misinfo, civic_misinfo_guided


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

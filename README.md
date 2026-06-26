# Testing AI assistants against misinformation and hidden propaganda

This project explores how AI assistants respond to suspicious civic information: misleading statistics, emotionally loaded local-news style content, hidden sponsorship, astroturfing, fake authority, conspiracy framing, and covert persuasion requests.

The aim is not to build a general misinformation detector. The aim is narrower: to evaluate whether an AI assistant can handle questionable civic content without amplifying it, laundering weak evidence, or helping users produce covertly manipulative material.

AI systems are increasingly used to summarise, explain, rewrite, and evaluate public information. This creates a subtle risk. Even when a model does not invent a false claim itself, it may still make misinformation more credible by summarising it too cleanly, removing uncertainty, repeating loaded framing, or treating weak sources as authoritative.

This project uses a small synthetic dataset of fictional civic-information scenarios to test whether models can preserve epistemic discipline under these conditions.

## What is being evaluated

The evaluation focuses on whether a model can:

* identify unsupported or weakly supported claims;
* flag missing provenance, unclear sourcing, or fake authority;
* notice misleading statistics, such as missing baselines or denominators;
* recognise advocacy presented as neutral information;
* avoid repeating loaded language as fact;
* preserve uncertainty when summarising contested material;
* refuse requests to create covert persuasion or hidden propaganda;
* redirect manipulative requests toward transparent, evidence-based communication.

## What this project is not

This project is not:

* a political persuasion tool;
* a classifier of real politicians, parties, or campaigns;
* a live misinformation monitoring system;
* a claim to detect all propaganda or misinformation;
* a substitute for expert judgement or fact-checking.

The dataset is synthetic and fictional. It avoids real parties, politicians, elections, and live controversies. The focus is on assistant behaviour, not on making claims about current political events.

## Deliverables

The repository contains:

* a label guide for common civic-information risk patterns;
* a small synthetic dataset with sample content, user requests, and expected behaviours;
* an advanced dataset generated from real published misinformation sources;
* Inspect-based evaluation scripts for running the samples against language models;
* optional GitHub Pages deployment of bundled Inspect logs using `inspect view bundle`.

## Project layout

* `src/misinfo_stress_test/tasks.py`: Inspect task entrypoints.
* `data/scenarios/*.md`: synthetic fictional scenarios.
* `data/advanced/*.md`: scenarios generated from real sources (see `docs/advanced-sources.md`).
* `scripts/fetch_advanced.py`: one-shot fetch that maps real-source labels into scenarios.
* `docs/label-guide.md`: label guide and expected assistant behaviours.
* `tests/`: deterministic tests for dataset loading, task construction, and rubric wiring.
* `Justfile`: common development and Inspect commands.

## How this evaluation works

Inspect runs separate roles:

* the solver model is the model being evaluated;
* the grader model scores the solver model's answer after it is produced.

The two roles can use the same underlying model, but they do not have to. The
`just eval` shortcut uses the same model for both roles for convenience. For
more serious comparisons, use a separate grader model that is stable and at
least as capable as the models under test.

This project is more than a thin Inspect wrapper. It adds:

* a human-editable Markdown scenario format with YAML front matter;
* `skip: true` for draft scenarios that should not enter evaluations;
* pytest-style scenario filtering over id, title, source, and risk labels;
* root-level scenario data outside the Python package source;
* unprompted and guided task variants, so you can compare default model
  behaviour against behaviour under explicit safety instructions;
* a domain-specific rubric for weak evidence, hidden sponsorship, misleading
  statistics, loaded framing, conspiracy framing, and covert persuasion;
* tests that validate parsing, filtering, task construction, and scorer wiring.

## Setup

This project uses `uv` and Python 3.14.

```sh
uv sync --group dev
```

Or with `just`:

```sh
just sync
```

## Running checks

```sh
just check
```

This runs formatting checks, linting, mypy, pytest, Inspect task discovery, and
a one-sample Inspect smoke test with `mockllm/model`.

Equivalent direct commands:

```sh
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv run inspect list tasks 'src/**/*.py'
```

Inspect writes trace and sample-buffer data under the user's application data
directory by default. In sandboxes or CI, set `HOME` and `INSPECT_TRACE_FILE` to
writable temporary paths, as the `just smoke` recipe does.

You can override the scenario and output directories used by `just`:

```sh
SCENARIOS_DIR=data/my-scenarios INSPECT_LOG_DIR=logs/dev just eval anthropic/claude-sonnet-4-5
INCLUDE_SOURCE_METADATA=true just eval anthropic/claude-sonnet-4-5 z-real-world
INSPECT_LOG_DIR=logs/dev INSPECT_BUNDLE_DIR=public/logs just bundle-logs
```

The supported path variables are:

* `SCENARIOS_DIR`: Markdown scenario directory, default `data/scenarios`.
* `INSPECT_LOG_DIR`: Inspect eval log directory, default `logs`.
* `INSPECT_BUNDLE_DIR`: bundled Inspect viewer output, default `logs-www`.
* `SMOKE_LOG_DIR`: smoke-test log directory, default `/private/tmp/misinfo-inspect-logs`.
* `INCLUDE_SOURCE_METADATA`: whether source fields are shown to the evaluated model,
  default `false`.
* `MODEL_CHOICES`: space-separated models shown by the interactive `just`
  selector, default `anthropic/claude-sonnet-4-5 openai/gpt-4.1-mini
  mockllm/model`.

## Running evaluations

List available Inspect tasks:

```sh
just list
```

Run the main task against a model:

```sh
just eval anthropic/claude-sonnet-4-5
```

Or pick from the predefined model menu:

```sh
just models
just eval select
just eval-select z-real-world
```

The `select` value works for `eval`, `eval-guided`, `eval-advanced`, and
`eval-advanced-guided`. The `*-select` recipes are shorter aliases. Override the
menu per run with `MODEL_CHOICES`:

```sh
MODEL_CHOICES="anthropic/claude-sonnet-4-5 openai/gpt-4.1-mini" just eval select
```

Run only matching scenarios with an optional pytest `-k`-style filter:

```sh
just eval anthropic/claude-sonnet-4-5 z-real-world
just eval anthropic/claude-sonnet-4-5 'climate and not conspiracy'
```

The filter matches scenario id, title, source fields, and risk-pattern labels. It
supports plain substring matching plus `and`, `or`, `not`, and parentheses.

The default task, `civic_misinfo`, is intentionally unprompted: the evaluated
model receives only the scenario and user request. This is meant to probe the
model's default behavior on suspicious civic information, not its obedience to a
strong safety prompt.

There is also a guided comparison task:

```sh
just eval-guided anthropic/claude-sonnet-4-5
```

The guided task, `civic_misinfo_guided`, adds an explicit system message about
epistemic discipline and covert persuasion. Use it to compare default behavior
against behavior under ideal instructions.

The advanced scenarios in `data/advanced` are ordinary Markdown scenarios, so
they use the same two tasks pointed at that directory. The `eval-advanced` and
`eval-advanced-guided` recipes are just shortcuts for that:

```sh
just eval-advanced anthropic/claude-sonnet-4-5
just eval-advanced anthropic/claude-sonnet-4-5 'conspired or euvsdisinfo'
# equivalently:
SCENARIOS_DIR=data/advanced just eval anthropic/claude-sonnet-4-5
```

These scenarios are generated from published datasets (CLIMATE-FEVER, LIAR,
EUvsDisinfo, ConspirED) by `scripts/fetch_advanced.py`, which maps each source's
native label into the scenario rubric. The scenario shown to the model stays
neutral; the source verdict and provenance live in the grader-only `## About`
section. See `docs/advanced-sources.md` for provenance, licensing, and the note
that this set deliberately uses real names and topics. Regenerate (one-shot,
needs network) with `just fetch-advanced`.

Both tasks use a model-graded rubric after the model answers. The grader prompt
is not shown to the evaluated model. The `just eval` shortcuts use the same
model as the grader:

```sh
just eval anthropic/claude-sonnet-4-5
```

For a separate grader model, call Inspect directly:

```sh
uv run inspect eval src/misinfo_stress_test/tasks.py@civic_misinfo \
  --model openai/gpt-4.1-mini \
  --model-role grader=anthropic/claude-sonnet-4-5 \
  -T scenarios_dir=data/scenarios \
  -T scenario_filter=z-real-world \
  --log-dir logs
```

Limit runs while developing:

```sh
uv run inspect eval src/misinfo_stress_test/tasks.py@civic_misinfo \
  --model mockllm/model \
  --model-role grader=mockllm/model \
  -T scenarios_dir=data/scenarios \
  --limit 1 \
  --log-dir logs
```

View logs:

```sh
just view
```

Bundle reviewed logs for static hosting:

```sh
just bundle-logs
```

## Adding a scenario

Each scenario is one Markdown file in `data/scenarios`.
Use the scenario id as the filename, for example `unsupported-claim-003.md`.
Files are loaded in filename-sorted order, so keep numeric suffixes zero-padded.

The evaluated model sees only `Scenario` and `User request` by default. The
`About` section, expected behavior, must-do/must-not lists, risk labels, and
source fields are retained for logs and grader context. Set
`INCLUDE_SOURCE_METADATA=true` if the source metadata should also be part of the
evaluated model's prompt.

```md
---
id: unsupported-claim-003
title: Example scenario title
source_type: real_source_context
source_url: "TODO: Add source URL or archive reference."
source_title: "TODO: Add source title."
source_outlet: "TODO: Add outlet/platform."
source_author: "TODO: Add author/account."
source_date: "TODO: Add publication date."
skip: false
risk_patterns:
  - unsupported_claim
  - missing_provenance
---

## About

Private evaluator context. This is shown to the grader and retained in logs, but
it is not shown to the evaluated model.

## Scenario

Long-form scenario text. This can be several paragraphs if needed.

## User request

The user's request to the assistant.

## Expected behavior

What a good assistant response should do.

## Must do

- Required behavior one.
- Required behavior two.

## Must not

- Prohibited behavior one.
- Prohibited behavior two.
```

Set `skip: true` while drafting a scenario. Skipped scenarios are excluded from
evaluation before the Markdown sections are parsed, so incomplete drafts can
remain in `data/scenarios` without breaking evals.

## Evaluation logs and safety note

Inspect logs can contain prompts, model outputs, metadata, scorer comments, and other information that may be unsuitable for public release.

This repository may include curated example logs generated from synthetic data. Raw logs should be reviewed before being committed or published.

If you run the evaluations with private prompts, real-world data, internal notes, API details, or non-public material, do not commit those logs.

## Real-world dataset resources

This repository currently uses synthetic fictional scenarios. If you add
real-world material, review the source licence, provenance, and label semantics
before importing it. Some datasets label claim truth, while others label source
credibility, state-backed origin, or propaganda narrative.

Useful starting points:

* [CLIMATE-FEVER](https://arxiv.org/abs/2012.00614): climate claims with
  evidence labels, useful for climate misinformation and uncertainty handling.
* [ClimateCheck 2026](https://arxiv.org/abs/2603.26449): shared-task work on
  scientific fact-checking and climate disinformation narrative classification.
* [EUvsDisinfo dataset](https://arxiv.org/abs/2406.12614): multilingual
  pro-Kremlin disinformation articles with trustworthy comparison articles.
* [Twitter/X information operations archive analysis](https://arxiv.org/abs/2305.05907):
  state-backed information-operation account data, useful for propaganda,
  astroturfing, and coordination-style tests.
* [Wired coverage of the Twitter IRA/Iran release](https://www.wired.com/story/twitter-troll-data-russia-ira-iran):
  background on the public release of state-linked information-operation data.
* [State-backed propaganda websites dataset](https://arxiv.org/abs/2310.14032):
  multilingual material from Russian state-backed propaganda ecosystems such as
  Reliable Recent News and WarOnFakes.
* [ConspirED](https://arxiv.org/abs/2508.20468): conspiracy-theory excerpts
  annotated for cognitive traits from the CONSPIR framework.
* [ConspEmoLLM](https://arxiv.org/abs/2403.06765): conspiracy detection and
  conspiracy-type tasks with affective features.
* [MultiFC](https://arxiv.org/abs/1909.03242): broad fact-checking claims from
  many fact-checking sites, with journalist-provided labels and metadata.
* [NELA-GT-2018](https://arxiv.org/abs/1904.01546) and
  [NELA-GT-2022](https://arxiv.org/abs/2203.05659): news corpora with
  outlet-level credibility labels.
* [LIAR](https://arxiv.org/abs/1705.00648): PolitiFact-derived short political
  statements with six-way truth labels.
* [FakeNewsNet](https://arxiv.org/abs/1809.01286): news and social-context data
  derived from fact-checking sources.
* [MM-COVID](https://arxiv.org/abs/2011.04088): multilingual, multimodal COVID
  misinformation and trustworthy-information data.

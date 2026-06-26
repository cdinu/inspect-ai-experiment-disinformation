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
* Inspect-based evaluation scripts for running the samples against language models;
* optional GitHub Pages deployment of bundled Inspect logs using `inspect view bundle`.

## Project layout

* `src/misinfo_stress_test/tasks.py`: Inspect task entrypoint.
* `data/scenarios/*.md`: synthetic fictional scenarios.
* `docs/label-guide.md`: label guide and expected assistant behaviours.
* `tests/`: deterministic tests for dataset loading, task construction, and rubric wiring.
* `Justfile`: common development and Inspect commands.

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
INSPECT_LOG_DIR=logs/dev INSPECT_BUNDLE_DIR=public/logs just bundle-logs
```

The supported path variables are:

* `SCENARIOS_DIR`: Markdown scenario directory, default `data/scenarios`.
* `INSPECT_LOG_DIR`: Inspect eval log directory, default `logs`.
* `INSPECT_BUNDLE_DIR`: bundled Inspect viewer output, default `logs-www`.
* `SMOKE_LOG_DIR`: smoke-test log directory, default `/private/tmp/misinfo-inspect-logs`.

## Running evaluations

List available Inspect tasks:

```sh
just list
```

Run the main task against a model:

```sh
just eval anthropic/claude-sonnet-4-5
```

Run only matching scenarios with an optional pytest `-k`-style filter:

```sh
just eval anthropic/claude-sonnet-4-5 z-real-world
just eval anthropic/claude-sonnet-4-5 'climate and not conspiracy'
```

The filter matches scenario id, title, source, and risk-pattern labels. It
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

Both tasks use a model-graded rubric after the model answers. The grader prompt
is not shown to the evaluated model. The `just eval` shortcuts use the same
model as the grader. For separate model roles, call Inspect directly:

```sh
uv run inspect eval src/misinfo_stress_test/tasks.py@civic_misinfo \
  --model anthropic/claude-sonnet-4-5 \
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

```md
---
id: unsupported-claim-003
title: Example scenario title
source: "TODO: Add source URL, dataset citation, or archive reference."
skip: false
risk_patterns:
  - unsupported_claim
  - missing_provenance
---

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

set shell := ["zsh", "-cu"]

export UV_CACHE_DIR := env_var_or_default("UV_CACHE_DIR", "/private/tmp/uv-cache")

scenarios_dir := env_var_or_default("SCENARIOS_DIR", "data/scenarios")
advanced_dir := env_var_or_default("ADVANCED_SCENARIOS_DIR", "data/advanced")
log_dir := env_var_or_default("INSPECT_LOG_DIR", "logs")
bundle_dir := env_var_or_default("INSPECT_BUNDLE_DIR", "docs/logs")
docs_dir := env_var_or_default("DOCS_DIR", "docs")
smoke_log_dir := env_var_or_default("SMOKE_LOG_DIR", "/private/tmp/misinfo-inspect-logs")
include_source_metadata := env_var_or_default("INCLUDE_SOURCE_METADATA", "false")
inspect_home := env_var_or_default("INSPECT_HOME", "/private/tmp/misinfo-inspect-home")
trace_file := env_var_or_default("INSPECT_TRACE_FILE", "/private/tmp/misinfo-inspect-trace.log")
model_choices := env_var_or_default("MODEL_CHOICES", "anthropic/claude-sonnet-4-5 mistral/mistral-medium-3-5 openrouter/free openrouter/deepseek/deepseek-v4-flash openrouter/xiaomi/mimo-v2.5 openrouter/tencent/hy3-preview openrouter/x-ai/grok-4.3 mockllm/model")
grader_model := env_var_or_default("GRADER_MODEL", "")

default:
    @just --list
    @printf '\nModels:\n'
    @printf '%s\n' {{model_choices}}

sync:
    uv sync --group dev

format:
    uv run ruff format .

format-check:
    uv run ruff format --check .

lint:
    uv run ruff check .

typecheck:
    uv run mypy src tests

test:
    uv run pytest

list:
    uv run inspect list tasks 'src/**/*.py'

models:
    @printf '%s\n' {{model_choices}}

eval model filter="":
    @mkdir -p {{log_dir}}
    @model_arg="{{model}}"; role_args=(); if [[ -n "{{grader_model}}" ]]; then role_args=(--model-role "grader={{grader_model}}"); elif [[ "$model_arg" != *,* ]]; then role_args=(--model-role "grader=$model_arg"); fi; filter_args=(); if [[ -n "{{filter}}" ]]; then filter_args=(-T "scenario_filter={{filter}}"); fi; HOME={{inspect_home}} INSPECT_TRACE_FILE={{trace_file}} uv run inspect eval src/misinfo_stress_test/tasks.py@civic_misinfo --model "$model_arg" "${role_args[@]}" -T scenarios_dir={{scenarios_dir}} -T include_source_metadata={{include_source_metadata}} "${filter_args[@]}" --log-dir {{log_dir}}

eval-guided model filter="":
    @mkdir -p {{log_dir}}
    @model_arg="{{model}}"; role_args=(); if [[ -n "{{grader_model}}" ]]; then role_args=(--model-role "grader={{grader_model}}"); elif [[ "$model_arg" != *,* ]]; then role_args=(--model-role "grader=$model_arg"); fi; filter_args=(); if [[ -n "{{filter}}" ]]; then filter_args=(-T "scenario_filter={{filter}}"); fi; HOME={{inspect_home}} INSPECT_TRACE_FILE={{trace_file}} uv run inspect eval src/misinfo_stress_test/tasks.py@civic_misinfo_guided --model "$model_arg" "${role_args[@]}" -T scenarios_dir={{scenarios_dir}} -T include_source_metadata={{include_source_metadata}} "${filter_args[@]}" --log-dir {{log_dir}}

# Multi-turn pressure task. Auto-runs only scenarios with a `## Pressure` section; optional filter narrows further.
eval-pressure model filter="":
    @mkdir -p {{log_dir}}
    @model_arg="{{model}}"; role_args=(); if [[ -n "{{grader_model}}" ]]; then role_args=(--model-role "grader={{grader_model}}"); elif [[ "$model_arg" != *,* ]]; then role_args=(--model-role "grader=$model_arg"); fi; filter_args=(); if [[ -n "{{filter}}" ]]; then filter_args=(-T "scenario_filter={{filter}}"); fi; HOME={{inspect_home}} INSPECT_TRACE_FILE={{trace_file}} uv run inspect eval src/misinfo_stress_test/tasks.py@civic_misinfo_pressure --model "$model_arg" "${role_args[@]}" -T scenarios_dir={{scenarios_dir}} -T include_source_metadata={{include_source_metadata}} "${filter_args[@]}" --log-dir {{log_dir}}

# Tool-grounding task (mock fetch_url). Auto-runs only scenarios with a `tool_sources` mapping; optional filter narrows further.
eval-grounded model filter="":
    @mkdir -p {{log_dir}}
    @model_arg="{{model}}"; role_args=(); if [[ -n "{{grader_model}}" ]]; then role_args=(--model-role "grader={{grader_model}}"); elif [[ "$model_arg" != *,* ]]; then role_args=(--model-role "grader=$model_arg"); fi; filter_args=(); if [[ -n "{{filter}}" ]]; then filter_args=(-T "scenario_filter={{filter}}"); fi; HOME={{inspect_home}} INSPECT_TRACE_FILE={{trace_file}} uv run inspect eval src/misinfo_stress_test/tasks.py@civic_misinfo_grounded --model "$model_arg" "${role_args[@]}" -T scenarios_dir={{scenarios_dir}} -T include_source_metadata={{include_source_metadata}} "${filter_args[@]}" --log-dir {{log_dir}}

smoke filter="":
    @mkdir -p {{smoke_log_dir}}
    @filter_args=(); if [[ -n "{{filter}}" ]]; then filter_args=(-T "scenario_filter={{filter}}"); fi; HOME={{inspect_home}} INSPECT_TRACE_FILE={{trace_file}} uv run inspect eval src/misinfo_stress_test/tasks.py@civic_misinfo --model mockllm/model --model-role grader=mockllm/model -T scenarios_dir={{scenarios_dir}} -T include_source_metadata={{include_source_metadata}} "${filter_args[@]}" --limit 1 --display none --log-dir {{smoke_log_dir}}

# Regenerate the advanced real-source scenarios (one-shot; needs network + openpyxl).
fetch-advanced source="all" per_label="3":
    uv run --with openpyxl python scripts/fetch_advanced.py --source {{source}} --per-label {{per_label}} --out-dir {{advanced_dir}}

eval-advanced model filter="":
    mkdir -p {{log_dir}}
    model_arg="{{model}}"; role_args=(); if [[ -n "{{grader_model}}" ]]; then role_args=(--model-role "grader={{grader_model}}"); elif [[ "$model_arg" != *,* ]]; then role_args=(--model-role "grader=$model_arg"); fi; filter_args=(); if [[ -n "{{filter}}" ]]; then filter_args=(-T "scenario_filter={{filter}}"); fi; HOME={{inspect_home}} INSPECT_TRACE_FILE={{trace_file}} uv run inspect eval src/misinfo_stress_test/tasks.py@civic_misinfo --model "$model_arg" "${role_args[@]}" -T scenarios_dir={{advanced_dir}} -T include_source_metadata={{include_source_metadata}} "${filter_args[@]}" --log-dir {{log_dir}}

eval-advanced-guided model filter="":
    mkdir -p {{log_dir}}
    model_arg="{{model}}"; role_args=(); if [[ -n "{{grader_model}}" ]]; then role_args=(--model-role "grader={{grader_model}}"); elif [[ "$model_arg" != *,* ]]; then role_args=(--model-role "grader=$model_arg"); fi; filter_args=(); if [[ -n "{{filter}}" ]]; then filter_args=(-T "scenario_filter={{filter}}"); fi; HOME={{inspect_home}} INSPECT_TRACE_FILE={{trace_file}} uv run inspect eval src/misinfo_stress_test/tasks.py@civic_misinfo_guided --model "$model_arg" "${role_args[@]}" -T scenarios_dir={{advanced_dir}} -T include_source_metadata={{include_source_metadata}} "${filter_args[@]}" --log-dir {{log_dir}}

view:
    uv run inspect view --log-dir {{log_dir}}

# Rank scenarios by difficulty (mean model-graded score) across all runs in the log dir.
# Optional task substring filter, e.g. `just hardest pressure`.
hardest task="":
    @HOME={{inspect_home}} uv run python scripts/scenario_difficulty.py --log-dir {{log_dir}} --task "{{task}}"

# Export the committed logs as a static viewer under docs/ for GitHub Pages,
# and inject the scenario-difficulty table into the docs landing page.
bundle-logs:
    uv run inspect view bundle --log-dir {{log_dir}} --output-dir {{bundle_dir}} --overwrite
    @touch {{docs_dir}}/.nojekyll
    @HOME={{inspect_home}} uv run python scripts/scenario_difficulty.py --log-dir {{log_dir}} --top 25 --html-into {{docs_dir}}/index.html
    @printf 'Bundled %s into %s. Landing page: %s/index.html\n' '{{log_dir}}' '{{bundle_dir}}' '{{docs_dir}}'

check: format-check lint typecheck test list smoke

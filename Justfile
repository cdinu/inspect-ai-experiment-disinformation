set shell := ["zsh", "-cu"]

export UV_CACHE_DIR := env_var_or_default("UV_CACHE_DIR", "/private/tmp/uv-cache")

scenarios_dir := env_var_or_default("SCENARIOS_DIR", "data/scenarios")
advanced_dir := env_var_or_default("ADVANCED_SCENARIOS_DIR", "data/advanced")
log_dir := env_var_or_default("INSPECT_LOG_DIR", "logs")
bundle_dir := env_var_or_default("INSPECT_BUNDLE_DIR", "logs-www")
smoke_log_dir := env_var_or_default("SMOKE_LOG_DIR", "/private/tmp/misinfo-inspect-logs")
include_source_metadata := env_var_or_default("INCLUDE_SOURCE_METADATA", "false")
inspect_home := env_var_or_default("INSPECT_HOME", "/private/tmp/misinfo-inspect-home")
trace_file := env_var_or_default("INSPECT_TRACE_FILE", "/private/tmp/misinfo-inspect-trace.log")
model_choices := env_var_or_default("MODEL_CHOICES", "anthropic/claude-sonnet-4-5 openrouter/free openrouter/deepseek/deepseek-v4-flash openrouter/x-ai/grok-4.3 mockllm/model")

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
    @selected_model="{{model}}"; if [[ "$selected_model" == "select" ]]; then choices=({{model_choices}}); PS3="Select model: "; select picked in "${choices[@]}"; do if [[ -n "$picked" ]]; then selected_model="$picked"; break; fi; echo "Invalid selection" >&2; done; fi; filter_args=(); if [[ -n "{{filter}}" ]]; then filter_args=(-T "scenario_filter={{filter}}"); fi; HOME={{inspect_home}} INSPECT_TRACE_FILE={{trace_file}} uv run inspect eval src/misinfo_stress_test/tasks.py@civic_misinfo --model "$selected_model" --model-role grader="$selected_model" -T scenarios_dir={{scenarios_dir}} -T include_source_metadata={{include_source_metadata}} "${filter_args[@]}" --log-dir {{log_dir}}

eval-guided model filter="":
    @mkdir -p {{log_dir}}
    @selected_model="{{model}}"; if [[ "$selected_model" == "select" ]]; then choices=({{model_choices}}); PS3="Select model: "; select picked in "${choices[@]}"; do if [[ -n "$picked" ]]; then selected_model="$picked"; break; fi; echo "Invalid selection" >&2; done; fi; filter_args=(); if [[ -n "{{filter}}" ]]; then filter_args=(-T "scenario_filter={{filter}}"); fi; HOME={{inspect_home}} INSPECT_TRACE_FILE={{trace_file}} uv run inspect eval src/misinfo_stress_test/tasks.py@civic_misinfo_guided --model "$selected_model" --model-role grader="$selected_model" -T scenarios_dir={{scenarios_dir}} -T include_source_metadata={{include_source_metadata}} "${filter_args[@]}" --log-dir {{log_dir}}

eval-select filter="":
    @just eval select "{{filter}}"

eval-guided-select filter="":
    @just eval-guided select "{{filter}}"

smoke filter="":
    @mkdir -p {{smoke_log_dir}}
    @filter_args=(); if [[ -n "{{filter}}" ]]; then filter_args=(-T "scenario_filter={{filter}}"); fi; HOME={{inspect_home}} INSPECT_TRACE_FILE={{trace_file}} uv run inspect eval src/misinfo_stress_test/tasks.py@civic_misinfo --model mockllm/model --model-role grader=mockllm/model -T scenarios_dir={{scenarios_dir}} -T include_source_metadata={{include_source_metadata}} "${filter_args[@]}" --limit 1 --display none --log-dir {{smoke_log_dir}}

# Regenerate the advanced real-source scenarios (one-shot; needs network + openpyxl).
fetch-advanced source="all" per_label="3":
    uv run --with openpyxl python scripts/fetch_advanced.py --source {{source}} --per-label {{per_label}} --out-dir {{advanced_dir}}

eval-advanced model filter="":
    mkdir -p {{log_dir}}
    selected_model="{{model}}"; if [[ "$selected_model" == "select" ]]; then choices=({{model_choices}}); PS3="Select model: "; select picked in "${choices[@]}"; do if [[ -n "$picked" ]]; then selected_model="$picked"; break; fi; echo "Invalid selection" >&2; done; fi; filter_args=(); if [[ -n "{{filter}}" ]]; then filter_args=(-T "scenario_filter={{filter}}"); fi; HOME={{inspect_home}} INSPECT_TRACE_FILE={{trace_file}} uv run inspect eval src/misinfo_stress_test/tasks.py@civic_misinfo --model "$selected_model" --model-role grader="$selected_model" -T scenarios_dir={{advanced_dir}} -T include_source_metadata={{include_source_metadata}} "${filter_args[@]}" --log-dir {{log_dir}}

eval-advanced-guided model filter="":
    mkdir -p {{log_dir}}
    selected_model="{{model}}"; if [[ "$selected_model" == "select" ]]; then choices=({{model_choices}}); PS3="Select model: "; select picked in "${choices[@]}"; do if [[ -n "$picked" ]]; then selected_model="$picked"; break; fi; echo "Invalid selection" >&2; done; fi; filter_args=(); if [[ -n "{{filter}}" ]]; then filter_args=(-T "scenario_filter={{filter}}"); fi; HOME={{inspect_home}} INSPECT_TRACE_FILE={{trace_file}} uv run inspect eval src/misinfo_stress_test/tasks.py@civic_misinfo_guided --model "$selected_model" --model-role grader="$selected_model" -T scenarios_dir={{advanced_dir}} -T include_source_metadata={{include_source_metadata}} "${filter_args[@]}" --log-dir {{log_dir}}

eval-advanced-select filter="":
    just eval-advanced select "{{filter}}"

eval-advanced-guided-select filter="":
    just eval-advanced-guided select "{{filter}}"

view:
    uv run inspect view --log-dir {{log_dir}}

bundle-logs:
    uv run inspect view bundle --log-dir {{log_dir}} --output-dir {{bundle_dir}} --overwrite

check: format-check lint typecheck test list smoke

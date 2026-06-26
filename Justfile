set shell := ["zsh", "-cu"]

export UV_CACHE_DIR := env_var_or_default("UV_CACHE_DIR", "/private/tmp/uv-cache")

scenarios_dir := env_var_or_default("SCENARIOS_DIR", "data/scenarios")
log_dir := env_var_or_default("INSPECT_LOG_DIR", "logs")
bundle_dir := env_var_or_default("INSPECT_BUNDLE_DIR", "logs-www")
smoke_log_dir := env_var_or_default("SMOKE_LOG_DIR", "/private/tmp/misinfo-inspect-logs")
inspect_home := env_var_or_default("INSPECT_HOME", "/private/tmp/misinfo-inspect-home")
trace_file := env_var_or_default("INSPECT_TRACE_FILE", "/private/tmp/misinfo-inspect-trace.log")

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

eval model filter="":
    mkdir -p {{log_dir}}
    filter_args=(); if [[ -n "{{filter}}" ]]; then filter_args=(-T "scenario_filter={{filter}}"); fi; HOME={{inspect_home}} INSPECT_TRACE_FILE={{trace_file}} uv run inspect eval src/misinfo_stress_test/tasks.py@civic_misinfo --model {{model}} --model-role grader={{model}} -T scenarios_dir={{scenarios_dir}} "${filter_args[@]}" --log-dir {{log_dir}}

eval-guided model filter="":
    mkdir -p {{log_dir}}
    filter_args=(); if [[ -n "{{filter}}" ]]; then filter_args=(-T "scenario_filter={{filter}}"); fi; HOME={{inspect_home}} INSPECT_TRACE_FILE={{trace_file}} uv run inspect eval src/misinfo_stress_test/tasks.py@civic_misinfo_guided --model {{model}} --model-role grader={{model}} -T scenarios_dir={{scenarios_dir}} "${filter_args[@]}" --log-dir {{log_dir}}

smoke filter="":
    mkdir -p {{smoke_log_dir}}
    filter_args=(); if [[ -n "{{filter}}" ]]; then filter_args=(-T "scenario_filter={{filter}}"); fi; HOME={{inspect_home}} INSPECT_TRACE_FILE={{trace_file}} uv run inspect eval src/misinfo_stress_test/tasks.py@civic_misinfo --model mockllm/model --model-role grader=mockllm/model -T scenarios_dir={{scenarios_dir}} "${filter_args[@]}" --limit 1 --display none --log-dir {{smoke_log_dir}}

view:
    uv run inspect view --log-dir {{log_dir}}

bundle-logs:
    uv run inspect view bundle --log-dir {{log_dir}} --output-dir {{bundle_dir}} --overwrite

check: format-check lint typecheck test list smoke

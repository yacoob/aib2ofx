# show action chooser
default:
  @just --choose


### dev recipes
#

lint:
  ruff check --fix

fmt:
  ruff format

typecheck:
  ty check

test:
  pytest -vvv


# run tests continuously
[no-cd]
continuous-test:
  watchexec -r -e py --shell=none just test

# test and generate coverage report
coverage:
  pytest -q --cov

# open coverage report in the browser
view-coverage:
  pytest -q --cov --cov-report=html:/tmp/aib2ofx-cov

# run all configured pre-commit checks, regardless of modified files
full-pre-commit: clean
  pre-commit run --all-files

# fmt, lint, typecheck, test
presubmit: fmt lint typecheck test


### setup recipes
#

# remove auxiliary run-time files
clean:
  #!/usr/bin/env bash
  shopt -s globstar
  rm -f **/.coverage
  rm -rf **/.pytest_cache/ **/.ruff_cache/ **/__pycache__/ **/dist

# remove aux files, destroy venv and the cached devshell
raze: clean
  rm -rf .venv .direnv


# check that the devshell is active
prereq-check:
  @if [ -z "${UV_PYTHON:-}" ]; then echo "devshell not active - run 'direnv allow' in the repo root"; exit 1; fi

# create venv, install deps, install and run a full pre-commit check set
init: prereq-check
  uv sync
  pre-commit install
  pre-commit run -a

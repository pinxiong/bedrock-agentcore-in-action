# uc01 · First Agent · convenience wrapper around run.py.
#
# This file holds no logic. Every target forwards to `run.py`, which is the real
# entry point and works on macOS, Linux and Windows alike. Use `make` if you have
# it, use `python3 run.py <target>` if you do not; the two are the same thing, and
# tests/copy_check.py asserts that these target lists have not drifted apart.
#
#     make check          ==  python3 run.py check
#     make deploy         ==  python3 run.py deploy
#
# The folder is self-contained, so a copy is a complete installation:
#     cp -r usecases/01-first-agent /tmp/uc01 && cd /tmp/uc01 && make doctor

.DEFAULT_GOAL := help
PY ?= python3

.PHONY: help check doctor sync unit test verify dev deploy status invoke traces logs down clean

help:  ## show this list
	@$(PY) run.py help

check:  ## assert this folder stands alone, by copying it
	@$(PY) run.py check

doctor:  ## check the toolchain, credentials and this folder
	@$(PY) run.py doctor

sync:  ## build the app environment from the lockfile
	@$(PY) run.py sync

unit:  ## run the offline unit tests, no AWS involved
	@$(PY) run.py unit

test:  ## run the capability assertions against the deployment
	@$(PY) run.py test

verify:  ## check + test, in that order
	@$(PY) run.py verify

dev:  ## run the agent locally, a real model, no deployment
	@$(PY) run.py dev

deploy:  ## deploy this use case on its own
	@$(PY) run.py deploy

status:  ## show the deployment state
	@$(PY) run.py status

invoke:  ## call the deployed agent
	@$(PY) run.py invoke

traces:  ## list recent traces
	@$(PY) run.py traces

logs:  ## tail the runtime logs
	@$(PY) run.py logs

down:  ## destroy only this use case
	@$(PY) run.py down

clean:  ## remove local build residue, never touches AWS
	@$(PY) run.py clean

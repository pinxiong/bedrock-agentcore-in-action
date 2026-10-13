# AgentCore in Action: top-level targets
#
# Use cases are independent, so every target takes one use case number:
#
#   make up      UC=05
#   make test    UC=05
#   make down    UC=05
#   make verify  UC=05      # assertions + coverage + independence checks
#
# Nothing here deploys more than one use case at a time, on purpose.

SHELL := /bin/bash
UC ?= 01

UC_DIR := $(shell ls -d usecases/$(UC)-* 2>/dev/null | head -1)

.PHONY: help check-dir up test down status verify verify-all list new

help:
	@echo "make up|test|down|status|verify UC=<NN>   (e.g. make test UC=05)"
	@echo "make list                                  use cases and their difficulty"
	@echo "make verify-all                            coverage + independence for the whole repo"
	@echo "make new SLUG=08-your-idea DIFFICULTY=5    scaffold a new use case"

check-dir:
	@if [ -z "$(UC_DIR)" ]; then \
	  echo "no use case directory matches usecases/$(UC)-* (not implemented yet?)" >&2; \
	  exit 1; \
	fi

up test down status: check-dir
	@$(MAKE) --no-print-directory -C $(UC_DIR) $@

verify: check-dir
	@$(MAKE) --no-print-directory -C $(UC_DIR) test
	@python3 shared/scripts/verify-coverage.py --usecase uc$(UC)

verify-all:
	python3 shared/scripts/verify-coverage.py --allow-missing-dirs

list:
	@python3 -c "import yaml,sys; s=yaml.safe_load(open('docs/05-capability-map.yaml')); \
	[print(f\"  {u['id']}  D{u['difficulty']}  {u['minutes']:>4} min  \${u['cost_usd']:>2}  {u['dir']}\") \
	 for u in s['usecases']+s['bonus']]"

new:
	@test -n "$(SLUG)" || { echo "usage: make new SLUG=08-your-idea DIFFICULTY=5" >&2; exit 1; }
	@test -n "$(DIFFICULTY)" || { echo "DIFFICULTY is required" >&2; exit 1; }
	./shared/scripts/new-usecase.sh $(SLUG) --difficulty $(DIFFICULTY)

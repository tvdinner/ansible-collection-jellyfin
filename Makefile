# tvdinner.jellyfin — Manage Jellyfin API keys, libraries and items.
# Uniform entry point (repo convention): CI runs exactly these targets.
# The repo is symlinked into a collection tree; tvdinner.core is cloned
# next to it (CORE_PATH overridable) so imports resolve in both directions.

PYTHON ?= python3
CORE_PATH ?= ../tvdinner-core

.PHONY: test lint check clean build-tree

build-tree:
	@mkdir -p build/ansible_collections/tvdinner
	@ln -sfn ../../.. build/ansible_collections/tvdinner/jellyfin
	@ln -sfn $(abspath $(CORE_PATH)) build/ansible_collections/tvdinner/core

test: build-tree
	PYTHONPATH=build $(PYTHON) -m pytest tests/ -v

lint: build-tree
	$(PYTHON) -m compileall -q plugins tests
	yamllint .
	$(PYTHON) -m flake8 plugins tests --max-line-length=120 --extend-ignore=E402

check: lint test

clean:
	rm -rf build

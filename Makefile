-include .env

default: help

# PARAMETERS
ESV_API_TOKEN ?= $$ESV_API_TOKEN
PYTHON3 ?= $$python3
VENV_NAME ?= .venv

# INTERNAL
_VENV_ACTIVATE = $(VENV_NAME)/bin/activate

.PHONY: help
help: ## (display this help message)
	@echo "Please use \`make <target>\` where <target> is one of:"
	@grep -h '^[a-zA-Z]' $(MAKEFILE_LIST) | sort | awk -F ':.*?## ' 'NF==2 {printf "\033[36m%-15s\033[0m%s\n", $$1, $$2}'

.PHONY: build
build: ## (build the docker image and tag with latest)
	docker build -t bible:latest .

.PHONY: clean
clean: venv ## PYTHON3=python3.9 VENV_NAME=.venv (clean up temp & local build files)
	. $(_VENV_ACTIVATE) && \
		pyclean .
	rm -rf *.egg-info
	rm -rf .mypy_cache/

.PHONY: install
install: venv ## PYTHON3=python3.9 VENV_NAME=.venv (install the application [including development dependencies] locally)
	. $(_VENV_ACTIVATE) && \
		pip install -e .[dev]; \

.PHONY: lint
lint: venv ## PYTHON3=python3.9 VENV_NAME=.venv (run flake8)
	. $(_VENV_ACTIVATE) && \
		flake8 bible

.PHONY: run
run: ## ESV_API_TOKEN (run the application inside an interactive docker container)
	docker run -it --rm -e ESV_API_TOKEN=$(ESV_API_TOKEN) bible:latest

.PHONY: run-local
run-local: ## PYTHON3=python3 VENV_NAME=.venv (run the application locally)
	. $(_VENV_ACTIVATE) && \
		python -ic "import bible; esv = bible.esv()"

.PHONY: venv
venv: $(_VENV_ACTIVATE) ## PYTHON3=python3.9 VENV_NAME=.venv (create a virtual env if it doesn't exist)

$(_VENV_ACTIVATE):
	`which $(PYTHON3)` -m venv $(VENV_NAME) && \
		. $@ && \
		pip install --upgrade pip
	touch $@

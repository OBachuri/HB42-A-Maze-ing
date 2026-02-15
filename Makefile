.ONESHELL:
SHELL := /bin/bash

NAME :=  a_maze_ing.py 

RM := rm -fr

RUN_ARGS := "config.txt"

TARGETS_WITH_ARGS := run debug

VENV_DIR := .mz-venv
PYTHON := python3
PIP := pip
C_DIR := pwd

BUILD_SOURCE_DIR := "mazegen-source"
WHEEL := $(BUILD_SOURCE_DIR)/dist/*.whl

MLX_URL := https://cdn.intra.42.fr/document/document/46143/mlx-2.2-py3-ubuntu-any.whl
MLX_ORIG := mlx-2.2-py3-ubuntu-any.whl
MLX_FIXED := mlx-2.2-py3-none-any.whl

OUTPUT_FILE := $(shell grep -i output_file config.txt | cut -d= -f2 | xargs)

define ACTIVATE_VENV
if [ -z "$$VIRTUAL_ENV" ]; then \
	echo "No virtual environment detected."; \
	$(MAKE) venv; \
	. "$(VENV_DIR)/bin/activate"; \
fi
endef

ifeq ($(filter $(firstword $(MAKECMDGOALS)),$(TARGETS_WITH_ARGS)),$(firstword $(MAKECMDGOALS)))
  EXTRA_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  ifneq ($(strip $(EXTRA_ARGS)),)
    RUN_ARGS := $(EXTRA_ARGS)  	
    $(eval $(RUN_ARGS):;@:)
  endif
endif

help:
	@echo "Start:"
	@echo "                 $$ make install"
	@echo "                 $$ make run config.txt"
	@echo ""
	@echo "Available targets:"
	@echo "  install        Install dependencies and set up the virtual environment"
	@echo "  re-build       Compile and install the wheel file of mazegen library"
	@echo "  run            Run the application"
	@echo "                 $$ make run config.txt"
	@echo "  lint           Run flake8 and mypy checks"
	@echo "  lint-strict    Run flake8 and strict mypy checks"
	@echo "  clean          Remove caches and temporary files"
	@echo "  fclean         clean + remove wheel file + remove folder of virtual environment"
	@echo "  debug          Run the debugger "	


re-build:
	@$(ACTIVATE_VENV)
	
	$(PYTHON) -m build $(BUILD_SOURCE_DIR)
	mv $(WHEEL) .
	$(RM) $(BUILD_SOURCE_DIR)/dist
	$(PIP) install mazegen-0.1.0-py3-none-any.whl

run:
	@$(ACTIVATE_VENV)
	$(PYTHON) ./$(NAME) $(RUN_ARGS)

debug:
	@$(ACTIVATE_VENV)
	python3 -m pdb ./$(NAME) $(RUN_ARGS)

check-venv:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "No virtual environment detected."; \
		$(MAKE) venv; \
		. "$(VENV_DIR)/bin/activate"; \
		echo "Virtual environment in $(VENV_DIR)."; \
	else \
		echo "Using virtual environment: $$VIRTUAL_ENV"; \
	fi

venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV_DIR); \
		chmod +x "$(VENV_DIR)/bin/activate" ; \
	else \
		echo "Virtual environment already exists."; \
	fi

clean:
	@$(RM) .mypy_cache
	@$(RM) __pycache__
	@$(RM) $(BUILD_SOURCE_DIR)/dist
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name *.egg-info -exec rm -rf {} +
	find . -name .pytest_cache -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	@if [ -f config.txt ]; then \
		rm -f "$(OUTPUT_FILE)"; \
	fi


fclean: clean
	@$(RM) $(VENV_DIR)
	@$(RM) *.whl

lint:
	@$(ACTIVATE_VENV)
	echo "--- flake8 test :"
	flake8 ./*.py $(BUILD_SOURCE_DIR)/
	echo "--- mypy test :"
	mypy ./*.py $(BUILD_SOURCE_DIR)/ \
		--warn-return-any \
		--warn-unused-ignores  \
		--ignore-missing-imports  \
		--disallow-untyped-defs \
		--check-untyped-defs \
		--exclude '(^\.mz-venv/|^test/|^subject/)'

lint-strict:
	@$(ACTIVATE_VENV)
	echo "--- flake8 test :"
	flake8 ./*.py $(BUILD_SOURCE_DIR)/
	echo "--- mypy strict test :"
	mypy . \
	--strict \
	--exclude '(^\.mz-venv/|^test/|^subject/)'

$(MLX_FIXED):
		wget -O $(MLX_ORIG) $(MLX_URL)
		mv -f $(MLX_ORIG) $(MLX_FIXED)

install: $(MLX_FIXED)
	@$(ACTIVATE_VENV)
	$(PIP) install pydantic dotenv build flake8 mypy
	$(PIP) install $(MLX_FIXED)
	$(PIP) install mazegen-0.1.0-py3-none-any.whl

.PHONY:	clean run debug install lint-strict lint $(RUN_ARGS) venv check-venv re-build help fclean
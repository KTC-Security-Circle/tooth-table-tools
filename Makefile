ENV := uno_r4_wifi
PIO := pio
UV  := uv
ANGLE ?=

.PHONY: help build upload monitor flash clean sync install test lint fmt move compile all

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

build: ## Compile the Arduino firmware
	$(PIO) run -e $(ENV)

upload: ## Flash the firmware to the board
	$(PIO) run -e $(ENV) -t upload

monitor: ## Open the serial monitor
	$(PIO) device monitor

flash: upload monitor ## Upload firmware then open the serial monitor

clean: ## Clean PlatformIO build artifacts
	$(PIO) run -e $(ENV) -t clean

sync: ## Install Python dependencies
	$(UV) sync

install: sync ## Alias for sync

test: ## Run the Python test suite
	$(UV) run pytest

lint: ## Lint the Python source with ruff
	$(UV) run ruff check .

fmt: ## Format the Python source with ruff
	$(UV) run ruff format .

move: ## Rotate the turntable, e.g. `make move ANGLE=45`
	$(UV) run python scripts/turntable.py $(ANGLE)

compile: ## Compile scripts/turntable.py into a standalone binary via Nuitka
	$(UV) run python -m nuitka --onefile --output-dir=dist --output-filename=turntable scripts/turntable.py

all: build compile test lint ## Build firmware, compile the binary, test, and lint

.PHONY: run install lint clean help

# ── Default ──────────────────────────────────────────────────
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Setup ────────────────────────────────────────────────────
install: ## Install all dependencies
	python -m pip install --upgrade pip
	pip install -r requirements.txt

install-dev: ## Install with dev tools
	python -m pip install --upgrade pip
	pip install -r requirements.txt ruff pytest

# ── Run ──────────────────────────────────────────────────────
run: ## Start the Streamlit app
	streamlit run app.py

# ── Quality ──────────────────────────────────────────────────
lint: ## Run linter
	ruff check . --select=E,F,I --ignore=E501

format: ## Auto-format code
	ruff format .

check: ## Validate syntax
	python -m py_compile app.py
	@echo "✅ Syntax OK"

# ── Cleanup ──────────────────────────────────────────────────
clean: ## Remove caches and temp files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov
	@echo "✅ Cleaned"

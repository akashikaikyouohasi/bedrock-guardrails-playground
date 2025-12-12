.PHONY: help install sync run shell clean test eval eval-setup cache-test cache-compare cache-metrics

# Default target
help:
	@echo "Available commands:"
	@echo "  make install        - Install dependencies using uv"
	@echo "  make sync           - Sync dependencies (install + update)"
	@echo "  make run            - Run examples (Claude Agent SDK + Bedrock)"
	@echo "  make shell          - Start IPython shell with agent loaded"
	@echo "  make clean          - Remove cache and temporary files"
	@echo "  make test           - Run tests (if available)"
	@echo "  make setup          - First-time setup (install + create .env)"
	@echo "  make eval-setup     - Install evaluation dependencies (DeepEval)"
	@echo "  make eval           - Run LLM evaluation with DeepEval"
	@echo ""
	@echo "Prompt Caching experiments:"
	@echo "  make cache-test     - Run basic prompt caching test"
	@echo "  make cache-compare  - Compare caching vs non-caching performance"
	@echo "  make cache-metrics  - Check CloudWatch metrics for cache effectiveness"

# Install dependencies
install:
	@echo "Installing dependencies with uv..."
	uv pip install -e .

# Sync dependencies (install + update)
sync:
	@echo "Syncing dependencies with uv..."
	uv sync

# Run examples (Claude Agent SDK)
run:
	@echo "Running examples (Claude Agent SDK with Bedrock)..."
	uv run python src/examples.py

# Start IPython shell
shell:
	@echo "Starting IPython shell..."
	@echo "Import agent: from src.agent import BedrockAgentSDK"
	uv run ipython

# Clean cache and temporary files
clean:
	@echo "Cleaning cache and temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete!"

# Run tests
test:
	@echo "Running tests..."
	uv run pytest tests/ -v

# Check environment
check-env:
	@echo "Checking environment variables..."
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found!"; \
		echo "Please copy .env.example to .env and configure it."; \
		exit 1; \
	fi
	@echo "Environment file exists ✓"

# Setup project (first time)
setup: install
	@echo "Setting up project..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo ".env file created from .env.example"; \
		echo "Please edit .env and add your credentials!"; \
	else \
		echo ".env file already exists"; \
	fi
	@echo "Setup complete!"

# Install evaluation dependencies
eval-setup:
	@echo "Installing evaluation dependencies (DeepEval + LangChain AWS)..."
	uv pip install -e ".[evaluation]"
	@echo "Evaluation setup complete!"
	@echo "Note: Using Bedrock Claude 3 Haiku for evaluation (via DeepEvalBaseLLM)"
	@echo "      AWS credentials must be set in .env"

# Run LLM evaluation with DeepEval
eval:
	@echo "Running LLM evaluation with DeepEval + Bedrock Haiku..."
	@echo "Note: This uses Bedrock Claude 3 Haiku for evaluation metrics"
	uv run python src/run_evaluation_deepeval.py

# Prompt Caching experiments
cache-test:
	@echo "Running basic Prompt Caching test..."
	@echo "This will send 3 requests with the same system prompt"
	uv run python experiments/prompt-caching/test_basic_caching.py

cache-compare:
	@echo "Comparing Prompt Caching effectiveness..."
	@echo "Testing short vs long system prompts"
	uv run python experiments/prompt-caching/test_comparison.py

cache-metrics:
	@echo "Checking CloudWatch metrics for Prompt Caching..."
	uv run python experiments/prompt-caching/check_cache_metrics.py

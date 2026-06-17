# Convenience targets. `make help` lists them.
.PHONY: help up down logs test build deploy

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n", $$1, $$2}'

up: ## Run the full stack locally (FastAPI :8000 + Next.js :3000)
	docker compose up --build

down: ## Stop the stack
	docker compose down

logs: ## Tail stack logs
	docker compose logs -f

test: ## Run the Python test suite
	python -m pytest -q

build: ## Production-build the dashboard
	cd frontend && npm run build

deploy: ## Publish the dashboard to Vercel (needs: npm i -g vercel)
	cd frontend && vercel --prod

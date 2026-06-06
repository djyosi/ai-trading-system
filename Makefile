.PHONY: dev test backend-test frontend-build

dev:
	docker compose up --build

test: backend-test frontend-build

backend-test:
	cd backend && python -m pytest -v

frontend-build:
	cd frontend && npm run build

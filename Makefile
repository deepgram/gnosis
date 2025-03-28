-include .env
export

LATEST_TAG := $(shell git describe --tags --abbrev=0 2>/dev/null || echo "0.0.0")
REDOC_CLI := npx @redocly/cli

# Test commands
test:
	pytest

# Dev commands
dev:
	python main.py

# Install dependencies
install:
	pip install -r requirements.txt

# Install development dependencies
install-dev:
	pip install -r requirements.txt
	pip install pytest flake8 black isort mypy

# Lint commands
lint:
	flake8 .
	black --check .
	isort --check .
	mypy .

# Format code
format:
	black .
	isort .

# Docs commands
build-docs:
	$(REDOC_CLI) build-docs docs/openapi.yaml \
		--theme.openapi.colors.primary.main="#00A89C" \
		--theme.openapi.typography.fontFamily="Inter, sans-serif" \
		--theme.openapi.onlyRequiredInSamples \
		--title="Gnosis API Documentation" \
		--output docs/index.html

view-docs:
	make build-docs && open docs/index.html

# Docker commands
build-image:
	docker buildx build --platform linux/amd64 --pull --rm -f "Dockerfile" \
		-t gnosis:latest \
		--build-arg VERSION=$(LATEST_TAG) \
		.

run-image:
	docker run -p 8080:8080 --rm -it \
	--env-file .env \
	gnosis:latest

tag-image:
	@echo "Tagging image with latest git tag: $(LATEST_TAG)"
	docker tag gnosis:latest quay.io/deepgram/gnosis:$(LATEST_TAG)

push-image:
	@echo "Pushing image to quay.io"
	docker push quay.io/deepgram/gnosis:$(LATEST_TAG)

nomad-plan:
	$(eval DEPLOY_CMD := $(shell nomad job plan -var version=$(LATEST_TAG) ../nomad-jobs/appeng/gnosis.nomad | grep "nomad job run" | tail -n 1))
	@echo "Planning gnosis job with version $(LATEST_TAG)"
	@echo "Running: nomad job plan -var version=$(LATEST_TAG)"

nomad-deploy: nomad-plan
	@echo "Deploying gnosis job with version $(LATEST_TAG)"
	@echo "Running: $(DEPLOY_CMD)"
	@$(DEPLOY_CMD)

.PHONY: test dev install install-dev lint format build-docs view-docs build-image run-image tag-image push-image nomad-plan nomad-deploy

-include .env
export

LATEST_TAG := $(shell git describe --tags --abbrev=0 2>/dev/null || echo "0.0.0")
REDOC_CLI := npx @redocly/cli
GOARCH := $(shell go env GOARCH)
GOOS := $(shell go env GOOS)

# Test commands
test:
	go test -timeout 10s ./...

# Dev commands
dev:
	go run ./cmd/main.go

# Build commands
build:
	CGO_ENABLED=0 GOOS=$(GOOS) GOARCH=$(GOARCH) go build -a -o bin/gnosis ./cmd/main.go

clean:
	rm -f bin/gnosis

# Lint commands
lint:
	npx prettier --write .
	$(HOME)/go/bin/golangci-lint run

install-lint:
	go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

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

.PHONY: build-image run-image tag-image push-image nomad-plan nomad-deploy test dev build clean lint install-lint build-docs view-docs

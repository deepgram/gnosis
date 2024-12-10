-include .env
export

test:
	go test -timeout 10s ./...

dev:
	go run ./cmd/main.go

build:
	go build -o bin/gnosis ./cmd/main.go

clean:
	rm -f bin/gnosis

lint:
	$(HOME)/go/bin/golangci-lint run
	npx markdownlint-cli2 "**/*.md" --config=.markdownlint.json --fix
	npx prettier --write .

install-lint:
	go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

build-docs:
	npx @redocly/cli build-docs docs/openapi.yaml \
		--theme.openapi.colors.primary.main="#00A89C" \
		--theme.openapi.typography.fontFamily="Inter, sans-serif" \
		--theme.openapi.onlyRequiredInSamples \
		--title="Gnosis API Documentation" \
		--output docs/index.html

view-docs:
	make build-docs && open docs/index.html

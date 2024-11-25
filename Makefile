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
	npx prettier --write .

build-docs:
	npx @redocly/cli build-docs api/openapi.yaml \
		--theme.openapi.colors.primary.main="#00A89C" \
		--theme.openapi.typography.headings.fontFamily="Inter, sans-serif" \
		--title="Gnosis API Documentation" \
		--output docs/index.html

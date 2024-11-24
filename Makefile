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

-include .env
export

test:
	go test -timeout 10s ./...

dev:
	go run ./cmd/main.go

build:
	go build -o bin/sage ./cmd/main.go

clean:
	rm -f bin/sage

lint:
	npx prettier --write .

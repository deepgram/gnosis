-include .env
export

test:
	go test -timeout 10s ./...

dev:
	go run ./cmd/main.go

build:
	go build -o bin/navi ./cmd/main.go

clean:
	rm -f bin/navi

lint:
	npx prettier --write .

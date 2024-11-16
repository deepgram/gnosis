test:
	go test -timeout 10s ./...

build:
	go build -o bin/navi ./cmd/main.go

clean:
	rm -f bin/navi

lint:
	npx prettier --write .

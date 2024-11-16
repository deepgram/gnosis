test:
	go test -v -race -timeout 30s ./...

build:
	go build -o bin/navi

clean:
	rm -f bin/navi

lint:
	npx prettier --write .

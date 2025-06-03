.PHONY: build run clean

build:
	GOOS=wasip1 GOARCH=wasm go build -o main.wasm .

run: build
	spin up --listen localhost:3000

clean:
	rm -f main.wasm

package main

import (
	"fmt"
	"net/http"

	spinhttp "github.com/fermyon/spin/sdk/go/v2/http"
)

func init() {
	spinhttp.Handle(func(w http.ResponseWriter, r *http.Request) {
		// For now, just test basic functionality
		// TODO: Once we figure out how to properly import the component,
		// we'll add the telemetry calls here

		w.Header().Set("Content-Type", "text/plain")
		w.WriteHeader(200)
		fmt.Fprintf(w, "Hello from Spin! Component test app is running.\n")
		fmt.Fprintf(w, "Request: %s %s\n", r.Method, r.URL.Path)
		fmt.Fprintf(w, "\nTODO: Add OpenTelemetry component integration\n")
	})
}

func main() {}

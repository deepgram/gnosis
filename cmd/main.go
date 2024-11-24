package main

import (
	"net/http"

	"github.com/deepgram/gnosis/internal/handlers"
	"github.com/deepgram/gnosis/internal/logger"
	"github.com/deepgram/gnosis/internal/services"
	"github.com/gorilla/mux"
)

func main() {
	logger.Info(logger.APP, "Starting Gnosis server")

	// Initialize services
	services, err := services.InitializeServices()
	if err != nil {
		logger.Fatal(logger.APP, "Failed to initialize services: %v", err)
	}

	// Initialize tools
	logger.Debug(logger.APP, "Setting up router")
	r := mux.NewRouter()

	// Static routes
	r.HandleFunc("/widget.js", handlers.HandleWidgetJS).Methods("GET")

	// v1 routes
	v1 := r.PathPrefix("/v1").Subrouter()
	v1.HandleFunc("/oauth/token", handlers.HandleTokenV1).Methods("POST")

	// Inject chat service into handler
	chatHandler := func(w http.ResponseWriter, r *http.Request) {
		handlers.HandleChatCompletionV1(services.GetChatService(), w, r)
	}
	v1.HandleFunc("/chat/completions", chatHandler).Methods("POST")

	logger.Debug(logger.APP, "Router setup complete")

	logger.Info(logger.APP, "Server starting on :8080")
	if err := http.ListenAndServe(":8080", r); err != nil {
		logger.Fatal(logger.APP, "ListenAndServe error: %v", err)
	}
}

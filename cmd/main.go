package main

import (
	"net/http"

	"github.com/deepgram/gnosis/internal/handlers"
	"github.com/deepgram/gnosis/internal/logger"
	"github.com/deepgram/gnosis/internal/services"
	"github.com/deepgram/gnosis/internal/services/tools"
	"github.com/gorilla/mux"
)

func main() {
	logger.Info(logger.APP, "Starting Gnosis server")

	// Initialize services
	if err := services.InitializeServices(); err != nil {
		logger.Fatal(logger.APP, "Failed to initialize services: %v", err)
	}

	// Initialize tools
	if err := tools.InitializeTools(); err != nil {
		logger.Fatal(logger.APP, "Failed to initialize tools: %v", err)
	}

	r := setupRouter()

	logger.Info(logger.APP, "Server starting on :8080")
	if err := http.ListenAndServe(":8080", r); err != nil {
		logger.Fatal(logger.APP, "ListenAndServe error: %v", err)
	}
}

func setupRouter() *mux.Router {
	logger.Debug(logger.APP, "Setting up router")
	r := mux.NewRouter()

	// Static routes
	r.HandleFunc("/widget.js", handlers.HandleWidgetJS).Methods("GET")

	// v1 routes
	v1 := r.PathPrefix("/v1").Subrouter()
	v1.HandleFunc("/oauth/token", handlers.HandleTokenV1).Methods("POST")
	v1.HandleFunc("/chat/completions", handlers.HandleChatCompletionV1).Methods("POST")

	logger.Debug(logger.APP, "Router setup complete")
	return r
}

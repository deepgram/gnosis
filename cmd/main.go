package main

import (
	"net/http"

	"github.com/deepgram/codename-sage/internal/handlers"
	"github.com/deepgram/codename-sage/internal/logger"
	"github.com/gorilla/mux"
)

func main() {
	logger.Info("Starting Sage server")
	r := setupRouter()

	logger.Info("Server starting on :8080")
	if err := http.ListenAndServe(":8080", r); err != nil {
		logger.Fatal("ListenAndServe error: %v", err)
	}
}

func setupRouter() *mux.Router {
	logger.Debug("Setting up router")
	r := mux.NewRouter()

	// v1 routes
	v1 := r.PathPrefix("/v1").Subrouter()
	v1.HandleFunc("/oauth/token", handlers.HandleTokenV1).Methods("POST")
	v1.HandleFunc("/chat/completions", handlers.HandleChatCompletionV1).Methods("POST")

	logger.Debug("Router setup complete")
	return r
}

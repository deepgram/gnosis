package main

import (
	"log"
	"net/http"

	"github.com/deepgram/codename-sage/internal/handlers"
	"github.com/deepgram/codename-sage/internal/logger"
	"github.com/gorilla/mux"
)

func main() {
	logger.Info("Starting Navi server")
	r := setupRouter()

	logger.Info("Server starting on :8080")
	if err := http.ListenAndServe(":8080", r); err != nil {
		logger.Error("ListenAndServe error: %v", err)
		log.Fatal(err)
	}
}

func setupRouter() *mux.Router {
	logger.Debug("Setting up router")
	r := mux.NewRouter()
	r.HandleFunc("/oauth/token", handlers.HandleToken).Methods("POST")
	r.HandleFunc("/chat/completions", handlers.HandleChatCompletion).Methods("POST")
	logger.Debug("Router setup complete")
	return r
}

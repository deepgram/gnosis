package main

import (
	"net/http"
	"time"

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
	v1.HandleFunc("/oauth/token", func(w http.ResponseWriter, r *http.Request) {
		handlers.HandleTokenV1(services.GetAuthCodeService(), w, r)
	}).Methods("POST")
	v1.HandleFunc("/oauth/authorize", func(w http.ResponseWriter, r *http.Request) {
		handlers.HandleAuthorizeV1(services.GetAuthCodeService(), w, r)
	}).Methods("POST")

	// Inject chat service into handler
	chatHandler := func(w http.ResponseWriter, r *http.Request) {
		handlers.HandleChatCompletionV1(services.GetChatService(), w, r)
	}
	v1.HandleFunc("/chat/completions", chatHandler).Methods("POST")

	logger.Debug(logger.APP, "Router setup complete")

	srv := &http.Server{
		Addr:         ":8080",
		Handler:      r,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	logger.Info(logger.APP, "Server starting on :8080")
	if err := srv.ListenAndServe(); err != nil {
		logger.Fatal(logger.APP, "ListenAndServe error: %v", err)
	}
}

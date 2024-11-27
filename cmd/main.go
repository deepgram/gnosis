package main

import (
	"net/http"
	"time"

	v1handlers "github.com/deepgram/gnosis/internal/api/v1/handlers"
	v1middleware "github.com/deepgram/gnosis/internal/api/v1/middleware"
	"github.com/deepgram/gnosis/internal/services"
	"github.com/deepgram/gnosis/pkg/logger"
	"github.com/gorilla/mux"
)

func main() {
	logger.Info(logger.APP, "Starting Gnosis server")

	// Initialize services
	services, err := services.InitializeServices()
	if err != nil {
		logger.Fatal(logger.APP, "Failed to initialize services: %v", err)
	}

	// Setup router
	logger.Debug(logger.APP, "Setting up router")
	r := mux.NewRouter()

	// v1 routes
	v1 := r.PathPrefix("/v1").Subrouter()

	// Public v1 routes (no auth required)
	v1publicRouter := v1.NewRoute().Subrouter()
	v1publicRouter.HandleFunc("/widget.js", v1handlers.HandleWidgetJSV1).Methods("GET")

	// OAuth v1 routes (no auth required)
	v1oauthRouter := v1.PathPrefix("/oauth").Subrouter()
	v1oauthRouter.HandleFunc("/token", func(w http.ResponseWriter, r *http.Request) {
		v1handlers.HandleTokenV1(services.GetAuthCodeService(), w, r)
	}).Methods("POST")
	v1oauthRouter.HandleFunc("/authorize", func(w http.ResponseWriter, r *http.Request) {
		v1handlers.HandleAuthorizeV1(services.GetAuthCodeService(), w, r)
	}).Methods("POST")

	// Protected v1 routes (require auth)
	v1protectedRouter := v1.NewRoute().Subrouter()
	v1protectedRouter.Use(v1middleware.RequireAuth([]string{"client_credentials", "authorization_code"}))

	// Protected v1 chat routes
	v1chatRouter := v1protectedRouter.PathPrefix("/chat").Subrouter()
	v1chatRouter.HandleFunc("/completions", func(w http.ResponseWriter, r *http.Request) {
		v1handlers.HandleChatCompletionV1(services.GetChatService(), w, r)
	}).Methods("POST")

	// Configure server
	srv := &http.Server{
		Addr:         ":8080",
		Handler:      r,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Start server
	logger.Info(logger.APP, "Server starting on :8080")
	if err := srv.ListenAndServe(); err != nil {
		logger.Fatal(logger.APP, "Server failed: %v", err)
	}
}

package main

import (
	"net/http"
	"time"

	"github.com/deepgram/gnosis/internal/api/v1/middleware"
	"github.com/deepgram/gnosis/internal/api/v1/routes"
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

	// Initialize tools
	logger.Debug(logger.APP, "Setting up router")
	r := mux.NewRouter()

	// v1 routes
	v1 := r.PathPrefix("/v1").Subrouter()

	// OAuth routes (no auth required)
	oauthRouter := v1.PathPrefix("/oauth").Subrouter()
	oauthRouter.HandleFunc("/token", func(w http.ResponseWriter, r *http.Request) {
		routes.HandleTokenV1(services.GetAuthCodeService(), w, r)
	}).Methods("POST")
	oauthRouter.HandleFunc("/authorize", func(w http.ResponseWriter, r *http.Request) {
		routes.HandleAuthorizeV1(services.GetAuthCodeService(), w, r)
	}).Methods("POST")

	// Public v1 routes (no auth required)
	publicRouter := v1.NewRoute().Subrouter()
	publicRouter.HandleFunc("/widget.js", routes.HandleWidgetJSV1).Methods("GET")

	// All other v1 routes (require auth)
	protectedRouter := v1.NewRoute().Subrouter()
	protectedRouter.Use(middleware.RequireAuth([]string{"client_credentials", "authorization_code"}))

	// Chat endpoints
	chatRouter := protectedRouter.PathPrefix("/chat").Subrouter()
	chatRouter.HandleFunc("/completions", func(w http.ResponseWriter, r *http.Request) {
		routes.HandleChatCompletionV1(services.GetChatService(), w, r)
	}).Methods("POST")

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

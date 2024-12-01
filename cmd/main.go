package main

import (
	"net/http"
	"os"
	"time"

	v1handlers "github.com/deepgram/gnosis/internal/api/v1/handlers"
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
		os.Exit(1)
	}

	// Setup router
	logger.Debug(logger.APP, "Setting up router")
	r := mux.NewRouter()

	/**
	 * Register all V1 routes
	 *	/v1/oauth/token - POST
	 *	/v1/oauth/widget - POST
	 *	/v1/widget.js - GET
	 *	/v1/chat/completions - POST
	 *	/v1/agent - WebSocket
	 */
	v1handlers.RegisterV1Routes(r, services)

	// Configure server
	srv := &http.Server{
		Addr:              ":8080",
		Handler:           r,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
		ReadHeaderTimeout: 15 * time.Second,
	}

	// Start server
	logger.Info(logger.APP, "Server starting on :8080")
	if err := srv.ListenAndServe(); err != nil {
		logger.Fatal(logger.APP, "Server failed: %v", err)
	}
}

package main

import (
	"log"
	"net/http"
	"time"

	v1handlers "github.com/deepgram/gnosis/internal/api/v1/handlers"
	"github.com/deepgram/gnosis/internal/services"
	"github.com/gorilla/mux"
)

func main() {
	// Initialize services
	services, err := services.InitializeServices()
	if err != nil {
		log.Fatalf("Failed to initialize services: %v", err)
	}

	// Setup router
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
	log.Println("Server starting on :8080")
	if err := srv.ListenAndServe(); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}

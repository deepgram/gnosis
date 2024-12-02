package main

import (
	"context"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	v1handlers "github.com/deepgram/gnosis/internal/api/v1/handlers"
	"github.com/deepgram/gnosis/internal/services"
	"github.com/gorilla/mux"
	"github.com/rs/zerolog"
)

func main() {
	// Initialize zerolog
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	log := zerolog.New(os.Stdout).With().Timestamp().Logger()

	// Initialize services
	services, err := services.InitializeServices()
	if err != nil {
		log.Fatal().Err(err).Msg("Critical failure initializing core services")
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
	log.Info().Msg("Server starting on :8080")
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatal().Err(err).Msg("Critical server failure - shutting down")
	}

	// Add graceful shutdown logging
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-c
		log.Warn().Msg("Server received interrupt signal - initiating graceful shutdown")
		if err := srv.Shutdown(context.Background()); err != nil {
			log.Fatal().Err(err).Msg("Error during server shutdown")
		}
		os.Exit(0)
	}()
}

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
	"github.com/rs/zerolog/log"
)

func main() {
	// Initialize zerolog
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix

	// Set log level from environment variable
	logLevel := os.Getenv("LOG_LEVEL")

	// Default to trace if not set
	if logLevel == "" {
		logLevel = "trace"
	}

	level, err := zerolog.ParseLevel(logLevel)

	if err != nil {
		log.Warn().Err(err).Msg("Invalid log level - defaulting to info")
		level = zerolog.InfoLevel // Default to info if invalid
	}

	zerolog.SetGlobalLevel(level)

	log := zerolog.New(os.Stdout).With().Timestamp().Logger()

	// Log environment variables
	log.Trace().
		Interface("env_vars", map[string]string{
			"LOG_LEVEL": os.Getenv("LOG_LEVEL"),
			"PORT":      os.Getenv("PORT"),
		}).
		Msg("Environment configuration loaded")

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

	// Log server configuration
	log.Trace().
		Interface("server_config", map[string]interface{}{
			"tls_enabled":          srv.TLSConfig != nil,
			"max_header_bytes":     srv.MaxHeaderBytes,
			"disable_http2":        srv.DisableGeneralOptionsHandler,
			"error_log_enabled":    srv.ErrorLog != nil,
			"base_context_defined": srv.BaseContext != nil,
		}).
		Msg("Detailed server configuration")

	// Log server details
	log.Debug().
		Str("address", ":8080").
		Str("server_name", srv.Addr).
		Int("read_timeout_sec", int(srv.ReadTimeout.Seconds())).
		Int("write_timeout_sec", int(srv.WriteTimeout.Seconds())).
		Int("idle_timeout_sec", int(srv.IdleTimeout.Seconds())).
		Int("read_header_timeout_sec", int(srv.ReadHeaderTimeout.Seconds())).
		Msg("Configuring HTTP server")

	// Start server
	log.Info().Msg("Server starting on :8080")
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatal().Err(err).Msg("Critical server failure - shutting down")
	}

	// Register OS signal handlers
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)

	// Log signal handlers
	log.Trace().
		Interface("signal_handlers", map[string]interface{}{
			"interrupt": true,
			"sigterm":   true,
		}).
		Msg("Registering OS signal handlers")

	// Handle OS signals
	go func() {
		<-c
		log.Debug().Msg("Initiating graceful shutdown sequence")

		log.Warn().Msg("Server received interrupt signal - initiating graceful shutdown")

		log.Debug().
			Int64("grace_period_ms", srv.IdleTimeout.Milliseconds()).
			Msg("Beginning server shutdown")

		if err := srv.Shutdown(context.Background()); err != nil {
			log.Fatal().Err(err).Msg("Error during server shutdown")
		}
		os.Exit(0)
	}()
}

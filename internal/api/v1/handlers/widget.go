package handlers

import (
	"net/http"

	"github.com/deepgram/gnosis/internal/services/session"
	"github.com/rs/zerolog/log"
)

func HandleWidgetJS(sessionService *session.Service, w http.ResponseWriter, r *http.Request) {
	log.Info().
		Str("client_ip", r.RemoteAddr).
		Str("user_agent", r.UserAgent()).
		Msg("Widget.js requested")

	// Create anonymous session
	if err := sessionService.CreateSession(w, ""); err != nil {
		log.Error().Err(err).Msg("Failed to create session for widget")
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}

	log.Info().
		Str("client_ip", r.RemoteAddr).
		Msg("Anonymous session created for widget")

	// Set appropriate headers
	w.Header().Set("Content-Type", "application/javascript")
	w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")
	w.Header().Set("Pragma", "no-cache")
	w.Header().Set("Expires", "0")

	// For now, return a simple console.log
	// This will be replaced with actual widget code later
	js := `
		console.log("Deepgram Gnosis Widget loaded");
		window.GNOSIS_WIDGET_ID = "gnosis-" + Math.random().toString(36).substring(2);
	`

	if _, err := w.Write([]byte(js)); err != nil {
		return
	}

	log.Info().
		Str("client_ip", r.RemoteAddr).
		Int("content_length", len(js)).
		Msg("Widget.js served successfully")
}

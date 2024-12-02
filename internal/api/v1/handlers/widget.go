package handlers

import (
	"crypto/sha256"
	"fmt"
	"net/http"
	"strconv"

	"github.com/deepgram/gnosis/internal/services/session"
	"github.com/rs/zerolog/log"
)

func HandleWidgetJS(sessionService *session.Service, w http.ResponseWriter, r *http.Request) {
	log.Info().Msg("Widget.js requested")

	log.Debug().
		Str("remote_addr", r.RemoteAddr).
		Str("user_agent", r.UserAgent()).
		Msg("Processing widget.js request")

	// Create anonymous session
	if err := sessionService.CreateSession(w, ""); err != nil {
		log.Error().Err(err).Msg("Failed to create session for widget")
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}

	log.Info().Msg("Anonymous session created for widget")

	log.Debug().
		Str("remote_addr", r.RemoteAddr).
		Msg("Anonymous session created for widget")

	// For now, return a simple console.log
	// This will be replaced with actual widget code later
	js := `console.log("Deepgram Gnosis Widget loaded");`

	// Set appropriate headers
	// https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers
	// Set Content-Type header to application/javascript since we're serving a JS file
	w.Header().Set("Content-Type", "application/javascript")

	// Cache-Control header set to cache publicly for 1 year
	w.Header().Set("Cache-Control", "public, max-age=31536000")

	// ETag header contains a content hash for cache validation
	w.Header().Set("ETag", `"`+fmt.Sprintf("%x", sha256.Sum256([]byte(js)))+`"`)

	// Content-Length header specifies the size of the response body in bytes
	w.Header().Set("Content-Length", strconv.Itoa(len(js)))

	// Prevent MIME type sniffing
	w.Header().Set("X-Content-Type-Options", "nosniff")

	// Prevent clickjacking by denying embedding in frames
	w.Header().Set("X-Frame-Options", "DENY")

	// Block XSS attacks
	w.Header().Set("X-XSS-Protection", "1; mode=block")

	// Restrict referrer information
	w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")

	// Restrict browser features
	w.Header().Set("Permissions-Policy", "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()")

	log.Debug().
		Str("remote_addr", r.RemoteAddr).
		Interface("headers", w.Header()).
		Msg("Set response headers for widget.js")

	if _, err := w.Write([]byte(js)); err != nil {
		return
	}

	log.Debug().
		Str("remote_addr", r.RemoteAddr).
		Int("js_size", len(js)).
		Msg("Returning widget JavaScript code")

	log.Info().Msg("Widget.js served successfully")
}

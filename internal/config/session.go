package config

import (
	"github.com/deepgram/gnosis/internal/logger"
)

var (
	// SessionCookieName is the name of the session cookie
	// Default to "gnosis_session" if not set in environment
	SessionCookieName = GetEnvOrDefault("SESSION_COOKIE_NAME", "gnosis_session")
)

// GetSessionCookieName returns the configured session cookie name
func GetSessionCookieName() string {
	logger.Debug(logger.CONFIG, "Getting session cookie name: %s", SessionCookieName)
	return SessionCookieName
}

// SetSessionCookieName temporarily changes the session cookie name and returns a function to restore it
// This is primarily used for testing
func SetSessionCookieName(name string) func() {
	logger.Debug(logger.CONFIG, "Temporarily changing session cookie name")
	previous := SessionCookieName
	SessionCookieName = name

	return func() {
		logger.Debug(logger.CONFIG, "Restoring previous session cookie name")
		SessionCookieName = previous
	}
}

package config

var (
	// SessionCookieName is the name of the session cookie
	// Default to "gnosis_session" if not set in environment
	SessionCookieName = GetEnvOrDefault("SESSION_COOKIE_NAME", "gnosis_session")
)

// GetSessionCookieName returns the configured session cookie name
func GetSessionCookieName() string {
	return SessionCookieName
}

// SetSessionCookieName temporarily changes the session cookie name and returns a function to restore it
// This is primarily used for testing
func SetSessionCookieName(name string) func() {
	previous := SessionCookieName
	SessionCookieName = name

	return func() {
		SessionCookieName = previous
	}
}

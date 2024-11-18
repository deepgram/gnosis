package config

import (
	"strings"
	"sync"
)

var (
	jwtSecretMu sync.RWMutex
	// JWTSecret is the secret key used to sign JWTs
	// In production, this should be loaded from environment variables
	JWTSecret = []byte(GetEnvOrDefault("JWT_SECRET", "your-256-bit-secret"))
)

// SetJWTSecret temporarily changes the JWT secret and returns a function to restore it
// This is primarily used for testing
func SetJWTSecret(secret []byte) func() {
	jwtSecretMu.Lock()
	previous := JWTSecret
	JWTSecret = secret
	jwtSecretMu.Unlock()

	return func() {
		jwtSecretMu.Lock()
		JWTSecret = previous
		jwtSecretMu.Unlock()
	}
}

// GetJWTSecret returns the current JWT secret in a thread-safe manner
func GetJWTSecret() []byte {
	jwtSecretMu.RLock()
	defer jwtSecretMu.RUnlock()
	return JWTSecret
}

// ClientConfig is a struct that contains the configuration for a client
type ClientConfig struct {
	ID          string
	Secret      string
	AllowedURLs []string // For CORS and referrer checking
	NoSecret    bool     // New field to indicate if client doesn't use a secret
}

// AllowedClients is a map of client types to their configurations
var AllowedClients = map[string]ClientConfig{
	"slack_bot": {
		ID:     GetEnvOrDefault("SAGE_SLACK_CLIENT_ID", ""),
		Secret: GetEnvOrDefault("SAGE_SLACK_CLIENT_SECRET", ""),
	},
	"discord_bot": {
		ID:     GetEnvOrDefault("SAGE_DISCORD_CLIENT_ID", ""),
		Secret: GetEnvOrDefault("SAGE_DISCORD_CLIENT_SECRET", ""),
	},
	"widget": {
		ID:       GetEnvOrDefault("SAGE_WIDGET_CLIENT_ID", ""),
		NoSecret: true, // Widget doesn't use a secret
		AllowedURLs: strings.Split(
			GetEnvOrDefault("SAGE_WIDGET_ALLOWED_URLS", "https://deepgram.com,https://www.deepgram.com"),
			",",
		),
	},
}

// GetClientTypeByID returns the client type (map key) for a given client ID,
// or an empty string if not found
func GetClientTypeByID(clientID string) string {
	for clientType, config := range AllowedClients {
		if config.ID == clientID {
			return clientType
		}
	}
	return ""
}

// GetClientConfig returns the client configuration for a given client type
func GetClientConfig(clientType string) ClientConfig {
	return AllowedClients[clientType]
}

const (
	GrantTypeAnonymous = "anonymous"
)

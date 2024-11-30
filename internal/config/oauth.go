package config

import (
	"fmt"
	"os"
	"strings"
	"sync"

	"github.com/deepgram/gnosis/pkg/logger"
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
	logger.Debug(logger.CONFIG, "Temporarily changing JWT secret")
	jwtSecretMu.Lock()
	previous := JWTSecret
	JWTSecret = secret
	jwtSecretMu.Unlock()

	return func() {
		logger.Debug(logger.CONFIG, "Restoring previous JWT secret")
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
	NoSecret    bool     // Indicate if client doesn't use a secret
	AllowedURLs []string // For CORS and referrer checking
	Scopes      []string // Specify scopes for the client
}

// AllowedClients is a map of client types to their configurations
var AllowedClients = scanForClientConfigs()

// init ensures the map is populated with valid configurations
func init() {
	logger.Info(logger.CONFIG, "Initializing OAuth client configurations")
	if len(AllowedClients) == 0 {
		logger.Fatal(logger.CONFIG, "No OAuth clients found in environment configuration")
		os.Exit(1)
	}

	// Validate each client configuration
	for clientType, client := range AllowedClients {
		// All clients require an ID
		if client.ID == "" {
			logger.Fatal(logger.CONFIG, "Missing required client ID for client: %s", clientType)
			os.Exit(1)
		}

		// Check if client requires a secret
		if !client.NoSecret && client.Secret == "" {
			logger.Fatal(logger.CONFIG, "Missing required secret for client: %s", clientType)
			os.Exit(1)
		}

		// Check if client requires allowed URLs
		if clientType == "widget" && len(client.AllowedURLs) == 0 {
			logger.Fatal(logger.CONFIG, "Missing required allowed URLs for widget client: %s", clientType)
			os.Exit(1)
		}

		logger.Info(logger.CONFIG, "Validated client configuration for: %s", clientType)
	}

	logger.Debug(logger.CONFIG, "OAuth client configuration initialization complete")
}

// GetClientTypeByID returns the client type (map key) for a given client ID,
// or an empty string if not found
func GetClientTypeByID(clientID string) string {
	logger.Debug(logger.CONFIG, "Looking up client type for client ID: %s", clientID)
	for clientType, config := range AllowedClients {
		if config.ID == clientID {
			logger.Debug(logger.CONFIG, "Found client type '%s' for client ID: %s", clientType, clientID)
			return clientType
		}
	}
	logger.Warn(logger.CONFIG, "No client type found for client ID: %s", clientID)
	return ""
}

// GetClientConfig returns the client configuration for a given client type
func GetClientConfig(clientType string) ClientConfig {
	config, exists := AllowedClients[clientType]
	if !exists {
		logger.Error(logger.CONFIG, "Attempted to get config for unknown client type: %s", clientType)
		return ClientConfig{}
	}
	logger.Debug(logger.CONFIG, "Retrieved config for client type: %s", clientType)
	return config
}

const (
	GrantTypeAnonymous = "anonymous"
)

func scanForClientConfigs() map[string]ClientConfig {
	clients := make(map[string]ClientConfig)

	// Get all environment variables
	for _, env := range os.Environ() {
		key := strings.Split(env, "=")[0]

		// Check if this is a GNOSIS client ID variable
		if strings.HasPrefix(key, "GNOSIS_") && strings.HasSuffix(key, "_CLIENT_ID") {
			// Extract the client type (e.g., "SLACK" from "GNOSIS_SLACK_CLIENT_ID")
			clientType := strings.ToLower(strings.TrimSuffix(
				strings.TrimPrefix(key, "GNOSIS_"),
				"_CLIENT_ID",
			))

			// Get the base prefix for this client's env vars
			prefix := fmt.Sprintf("GNOSIS_%s", strings.ToUpper(clientType))

			// Create client config
			config := ClientConfig{
				ID:          GetEnvOrDefault(fmt.Sprintf("%s_CLIENT_ID", prefix), ""),
				Secret:      GetEnvOrDefault(fmt.Sprintf("%s_CLIENT_SECRET", prefix), ""),
				NoSecret:    GetEnvOrDefault(fmt.Sprintf("%s_NO_SECRET", prefix), "false") == "true",
				AllowedURLs: strings.Split(GetEnvOrDefault(fmt.Sprintf("%s_ALLOWED_URLS", prefix), ""), ","),
				Scopes:      strings.Split(GetEnvOrDefault(fmt.Sprintf("%s_SCOPES", prefix), ""), ","),
			}

			// Clean up empty strings from slice fields
			config.AllowedURLs = cleanEmptyStrings(config.AllowedURLs)
			config.Scopes = cleanEmptyStrings(config.Scopes)

			// Assign to map
			clients[clientType] = config
			logger.Info(logger.CONFIG, "Loaded client configuration for: %s", clientType)
		}
	}

	return clients
}

// Helper function to clean empty strings from slices
func cleanEmptyStrings(slice []string) []string {
	result := make([]string, 0)
	for _, s := range slice {
		if s != "" {
			result = append(result, s)
		}
	}
	return result
}

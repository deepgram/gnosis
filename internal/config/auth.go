package config

import (
	"sync"
)

var (
	jwtSecretMu sync.RWMutex
	// JWTSecret is the secret key used to sign JWTs
	// In production, this should be loaded from environment variables
	JWTSecret = []byte(getEnvOrDefault("JWT_SECRET", "your-256-bit-secret"))
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

package config

import (
	"os"

	"github.com/deepgram/codename-sage/internal/logger"
)

// getEnvOrDefault returns the value of an environment variable or a default value
func GetEnvOrDefault(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" && defaultValue == "" {
		logger.Warn("Empty value and default for environment variable: %s", key)
	}
	if value == "" {
		return defaultValue
	}
	return value
}

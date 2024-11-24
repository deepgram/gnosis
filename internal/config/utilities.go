package config

import (
	"os"

	"github.com/deepgram/gnosis/internal/logger"
)

// getEnvOrDefault returns the value of an environment variable or a default value
func GetEnvOrDefault(key, defaultValue string) string {
	logger.Debug(logger.CONFIG, "Getting environment variable: %s with default: %s", key, defaultValue)

	value := os.Getenv(key)

	if value == "" && defaultValue == "" {
		logger.Warn(logger.CONFIG, "Empty value and default for environment variable: %s", key)
		return ""
	}

	if value == "" {
		logger.Info(logger.CONFIG, "Environment variable %s not set, using default value", key)
		return defaultValue
	}

	logger.Debug(logger.CONFIG, "Retrieved environment variable %s with value: %s", key, value)
	return value
}

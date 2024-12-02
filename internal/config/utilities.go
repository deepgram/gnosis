package config

import (
	"os"
)

// getEnvOrDefault returns the value of an environment variable or a default value
func GetEnvOrDefault(key, defaultValue string) string {
	value := os.Getenv(key)

	if value == "" && defaultValue == "" {
		return ""
	}

	if value == "" {
		return defaultValue
	}

	return value
}

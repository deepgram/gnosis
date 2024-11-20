package config

import (
	"github.com/deepgram/codename-sage/internal/logger"
)

func GetKapaProjectID() string {
	logger.Debug("Attempting to retrieve KAPA project ID from environment")
	value := GetEnvOrDefault("KAPA_PROJECT_ID", "")
	if value == "" {
		logger.Error("Failed to retrieve KAPA project ID - environment variable not set")
	} else {
		logger.Info("KAPA project ID successfully loaded")
	}
	return value
}

func GetKapaAPIKey() string {
	logger.Debug("Attempting to retrieve KAPA API key from environment")
	value := GetEnvOrDefault("KAPA_API_KEY", "")
	if value == "" {
		logger.Error("Failed to retrieve KAPA API key - environment variable not set")
	} else {
		logger.Info("KAPA API key successfully loaded")
	}
	return value
}

func GetKapaIntegrationID() string {
	logger.Debug("Attempting to retrieve KAPA integration ID from environment")
	value := GetEnvOrDefault("KAPA_INTEGRATION_ID", "")
	if value == "" {
		logger.Error("Failed to retrieve KAPA integration ID - environment variable not set")
	} else {
		logger.Info("KAPA integration ID successfully loaded")
	}
	return value
}

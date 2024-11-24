package config

import (
	"github.com/deepgram/gnosis/internal/logger"
)

func GetKapaProjectID() string {
	logger.Debug(logger.CONFIG, "Attempting to retrieve KAPA project ID from environment")
	value := GetEnvOrDefault("KAPA_PROJECT_ID", "")
	if value == "" {
		logger.Warn(logger.CONFIG, "Failed to retrieve KAPA project ID - environment variable not set")
	} else {
		logger.Info(logger.CONFIG, "KAPA project ID successfully loaded")
	}
	return value
}

func GetKapaAPIKey() string {
	logger.Debug(logger.CONFIG, "Attempting to retrieve KAPA API key from environment")
	value := GetEnvOrDefault("KAPA_API_KEY", "")
	if value == "" {
		logger.Error(logger.CONFIG, "Failed to retrieve KAPA API key - environment variable not set")
	} else {
		logger.Info(logger.CONFIG, "KAPA API key successfully loaded")
	}
	return value
}

func GetKapaIntegrationID() string {
	logger.Debug(logger.CONFIG, "Attempting to retrieve KAPA integration ID from environment")
	value := GetEnvOrDefault("KAPA_INTEGRATION_ID", "")
	if value == "" {
		logger.Error(logger.CONFIG, "Failed to retrieve KAPA integration ID - environment variable not set")
	} else {
		logger.Info(logger.CONFIG, "KAPA integration ID successfully loaded")
	}
	return value
}

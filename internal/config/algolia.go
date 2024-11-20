package config

import (
	"github.com/deepgram/codename-sage/internal/logger"
)

func GetAlgoliaAppID() string {
	logger.Debug("Getting Algolia App ID from environment")
	value := GetEnvOrDefault("ALGOLIA_APP_ID", "")
	if value == "" {
		logger.Error("ALGOLIA_APP_ID environment variable not set")
		return value
	}
	logger.Info("Successfully retrieved Algolia App ID")
	return value
}

func GetAlgoliaAPIKey() string {
	logger.Debug("Getting Algolia API Key from environment")
	value := GetEnvOrDefault("ALGOLIA_API_KEY", "")
	if value == "" {
		logger.Error("ALGOLIA_API_KEY environment variable not set")
		return value
	}
	logger.Info("Successfully retrieved Algolia API Key")
	return value
}

func GetAlgoliaIndexName() string {
	logger.Debug("Getting Algolia Index Name from environment")
	value := GetEnvOrDefault("ALGOLIA_INDEX_NAME", "")
	if value == "" {
		logger.Error("ALGOLIA_INDEX_NAME environment variable not set")
		return value
	}
	logger.Info("Successfully retrieved Algolia Index Name")
	return value
}

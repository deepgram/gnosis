package config

import (
	"github.com/deepgram/gnosis/internal/logger"
)

func GetAlgoliaAppID() string {
	logger.Debug(logger.CONFIG, "Getting Algolia App ID from environment")
	value := GetEnvOrDefault("ALGOLIA_APP_ID", "")
	if value == "" {
		logger.Warn(logger.CONFIG, "ALGOLIA_APP_ID environment variable not set")
		return value
	}
	logger.Info(logger.CONFIG, "Successfully retrieved Algolia App ID")
	return value
}

func GetAlgoliaAPIKey() string {
	logger.Debug(logger.CONFIG, "Getting Algolia API Key from environment")
	value := GetEnvOrDefault("ALGOLIA_API_KEY", "")
	if value == "" {
		logger.Error(logger.CONFIG, "ALGOLIA_API_KEY environment variable not set")
		return value
	}
	logger.Info(logger.CONFIG, "Successfully retrieved Algolia API Key")
	return value
}

func GetAlgoliaIndexName() string {
	logger.Debug(logger.CONFIG, "Getting Algolia Index Name from environment")
	value := GetEnvOrDefault("ALGOLIA_INDEX_NAME", "")
	if value == "" {
		logger.Error(logger.CONFIG, "ALGOLIA_INDEX_NAME environment variable not set")
		return value
	}
	logger.Info(logger.CONFIG, "Successfully retrieved Algolia Index Name")
	return value
}

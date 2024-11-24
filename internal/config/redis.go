package config

import (
	"github.com/deepgram/gnosis/internal/logger"
)

func GetRedisURL() string {
	logger.Debug(logger.CONFIG, "Attempting to retrieve Redis URL from environment")
	value := GetEnvOrDefault("REDIS_URL", "")
	if value == "" {
		logger.Warn(logger.CONFIG, "Failed to retrieve Redis URL - environment variable not set")
	} else {
		logger.Info(logger.CONFIG, "Redis URL successfully loaded")
	}
	return value
}

func GetRedisPassword() string {
	logger.Debug(logger.CONFIG, "Attempting to retrieve Redis password from environment")
	value := GetEnvOrDefault("REDIS_PASSWORD", "")
	if value == "" {
		logger.Warn(logger.CONFIG, "Failed to retrieve Redis password - environment variable not set")
	} else {
		logger.Info(logger.CONFIG, "Redis password successfully loaded")
	}
	return value
}

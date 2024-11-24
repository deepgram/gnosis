package config

import (
	"github.com/deepgram/gnosis/internal/logger"
)

func GetRedisURL() string {
	logger.Debug("Getting Redis URL from environment")
	return GetEnvOrDefault("REDIS_URL", "")
}

func GetRedisPassword() string {
	logger.Debug("Getting Redis password from environment")
	return GetEnvOrDefault("REDIS_PASSWORD", "")
}

func IsRedisConfigured() bool {
	return GetRedisURL() != ""
}

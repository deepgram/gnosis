package config

import (
	"strconv"
	"time"

	"github.com/deepgram/gnosis/pkg/logger"
)

type RateLimitConfig struct {
	Enabled bool
	MaxHits int
	Window  time.Duration
}

func GetRateLimitConfig(key string) RateLimitConfig {
	enabled := GetEnvOrDefault("RATELIMIT_ENABLED", "false") == "true"

	configs := map[string]RateLimitConfig{
		"global": {
			Enabled: enabled,
			MaxHits: parseEnvInt("RATELIMIT_GLOBAL", 1000), // 1000 requests per minute globally
			Window:  time.Minute,
		},
		"oauth_token": {
			Enabled: enabled,
			MaxHits: parseEnvInt("RATELIMIT_OAUTH_TOKEN", 30), // 30 requests per minute
			Window:  time.Minute,
		},
		"oauth_widget": {
			Enabled: enabled,
			MaxHits: parseEnvInt("RATELIMIT_OAUTH_WIDGET", 60), // 60 requests per minute
			Window:  time.Minute,
		},
		"chat_completion": {
			Enabled: enabled,
			MaxHits: parseEnvInt("RATELIMIT_CHAT_COMPLETION", 120), // 120 requests per minute
			Window:  time.Minute,
		},
	}

	if config, exists := configs[key]; exists {
		return config
	}

	logger.Warn(logger.CONFIG, "No rate limit config found for key: %s", key)
	return RateLimitConfig{Enabled: false}
}

func parseEnvInt(key string, defaultValue int) int {
	val := GetEnvOrDefault(key, "")
	if val == "" {
		return defaultValue
	}

	parsed, err := strconv.Atoi(val)
	if err != nil {
		logger.Warn(logger.CONFIG, "Invalid value for %s, using default: %d", key, defaultValue)
		return defaultValue
	}

	return parsed
}

package config

import "github.com/deepgram/gnosis/pkg/logger"

// GetOpenAIKey returns the current OpenAI key
func GetOpenAIKey() string {
	logger.Debug(logger.CONFIG, "Attempting to retrieve OpenAI key from environment")
	value := GetEnvOrDefault("OPENAI_KEY", "")
	if value == "" {
		logger.Warn(logger.CONFIG, "Failed to retrieve OpenAI key - environment variable not set")
	} else {
		logger.Info(logger.CONFIG, "OpenAI key successfully loaded")
	}
	return value
}

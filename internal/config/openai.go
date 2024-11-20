package config

import "github.com/deepgram/codename-sage/internal/logger"

// GetOpenAIKey returns the current OpenAI key
func GetOpenAIKey() string {
	logger.Debug("Attempting to retrieve OpenAI key from environment")
	value := GetEnvOrDefault("OPENAI_KEY", "")
	if value == "" {
		logger.Error("Failed to retrieve OpenAI key - environment variable not set")
	} else {
		logger.Info("OpenAI key successfully loaded")
	}
	return value
}

package config

import "github.com/rs/zerolog/log"

// GetOpenAIKey returns the current OpenAI key
func GetOpenAIKey() string {
	value := GetEnvOrDefault("OPENAI_KEY", "")
	if value == "" {
		log.Fatal().Msg("OPENAI_KEY environment variable not set")
	}
	return value
}

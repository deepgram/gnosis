package config

import "log"

// GetOpenAIKey returns the current OpenAI key
func GetOpenAIKey() string {
	value := GetEnvOrDefault("OPENAI_KEY", "")
	if value == "" {
		log.Fatal("OPENAI_KEY environment variable not set")
	}
	return value
}

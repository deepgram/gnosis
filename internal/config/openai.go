package config

var (
	openaiKey = getEnvOrDefault("OPENAI_KEY", "")
)

// GetOpenAIKey returns the current OpenAI key in a thread-safe manner
func GetOpenAIKey() []byte {
	return []byte(openaiKey)
}

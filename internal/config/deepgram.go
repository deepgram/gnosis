package config

func GetDeepgramAPIKey() string {
	return GetEnvOrDefault("DEEPGRAM_API_KEY", "")
}

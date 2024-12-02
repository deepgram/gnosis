package config

func GetRedisURL() string {
	return GetEnvOrDefault("REDIS_URL", "")
}

func GetRedisPassword() string {
	return GetEnvOrDefault("REDIS_PASSWORD", "")
}

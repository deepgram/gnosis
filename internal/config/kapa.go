package config

func GetKapaProjectID() string {
	return getEnvOrDefault("KAPA_PROJECT_ID", "")
}

func GetKapaAPIKey() string {
	return getEnvOrDefault("KAPA_API_KEY", "")
}

func GetKapaIntegrationID() string {
	return getEnvOrDefault("KAPA_INTEGRATION_ID", "")
}

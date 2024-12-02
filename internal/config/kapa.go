package config

func GetKapaProjectID() string {
	return GetEnvOrDefault("KAPA_PROJECT_ID", "")
}

func GetKapaAPIKey() string {
	return GetEnvOrDefault("KAPA_API_KEY", "")
}

func GetKapaIntegrationID() string {
	return GetEnvOrDefault("KAPA_INTEGRATION_ID", "")
}

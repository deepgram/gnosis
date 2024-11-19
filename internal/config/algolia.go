package config

func GetAlgoliaAppID() string {
	return GetEnvOrDefault("ALGOLIA_APP_ID", "")
}

func GetAlgoliaAPIKey() string {
	return GetEnvOrDefault("ALGOLIA_API_KEY", "")
}

func GetAlgoliaIndexName() string {
	return GetEnvOrDefault("ALGOLIA_INDEX_NAME", "")
}

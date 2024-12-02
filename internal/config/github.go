package config

func GetGitHubToken() string {
	return GetEnvOrDefault("GITHUB_TOKEN", "")
}

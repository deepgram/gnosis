package config

import (
	"github.com/deepgram/codename-sage/internal/logger"
)

func GetGitHubToken() string {
	value := GetEnvOrDefault("GITHUB_TOKEN", "")
	if value == "" {
		logger.Warn("GITHUB_TOKEN environment variable not set")
	} else {
		logger.Debug("GitHub token successfully loaded")
	}
	return value
}

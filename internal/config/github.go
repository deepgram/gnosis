package config

import (
	"github.com/deepgram/gnosis/internal/logger"
)

func GetGitHubToken() string {
	logger.Debug(logger.CONFIG, "Getting GitHub token from environment")
	value := GetEnvOrDefault("GITHUB_TOKEN", "")
	if value == "" {
		logger.Warn(logger.CONFIG, "GITHUB_TOKEN environment variable not set")
		return value
	}
	logger.Info(logger.CONFIG, "Successfully retrieved GitHub token")
	return value
}

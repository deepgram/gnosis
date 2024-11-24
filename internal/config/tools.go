package config

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/deepgram/gnosis/internal/logger"
)

type ToolDefinition struct {
	Name        string                 `json:"name"`
	Description string                 `json:"description"`
	Parameters  map[string]interface{} `json:"parameters"`
}

type ToolsConfig struct {
	Tools []ToolDefinition `json:"tools"`
}

func LoadToolsConfig(configPath string) (*ToolsConfig, error) {
	data, err := os.ReadFile(configPath)
	if err != nil {
		logger.Error(logger.CONFIG, "Failed to read tools config: %v", err)
		return nil, fmt.Errorf("failed to read tools config: %w", err)
	}

	var config ToolsConfig
	if err := json.Unmarshal(data, &config); err != nil {
		logger.Error(logger.CONFIG, "Failed to parse tools config: %v", err)
		return nil, fmt.Errorf("failed to parse tools config: %w", err)
	}

	return &config, nil
}

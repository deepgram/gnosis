package config

import (
	"encoding/json"
	"fmt"
	"os"
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
		return nil, fmt.Errorf("failed to read tools config: %w", err)
	}

	var config ToolsConfig
	if err := json.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("failed to parse tools config: %w", err)
	}

	return &config, nil
}

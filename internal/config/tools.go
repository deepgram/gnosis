package config

import (
	"encoding/json"
	"log"
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
		log.Fatalf("Failed to read tools config: %v", err)
	}

	var config ToolsConfig
	if err := json.Unmarshal(data, &config); err != nil {
		log.Fatalf("failed to parse tools config: %v", err)
	}

	return &config, nil
}

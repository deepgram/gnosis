package config

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/rs/zerolog/log"
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
		log.Error().
			Err(err).
			Str("path", configPath).
			Msg("Failed to read critical tools configuration file")
		return nil, fmt.Errorf("failed to read tools config: %w", err)
	}

	var config ToolsConfig
	if err := json.Unmarshal(data, &config); err != nil {
		log.Error().
			Err(err).
			Str("path", configPath).
			Msg("Failed to parse critical tools configuration")
		return nil, fmt.Errorf("failed to parse tools config: %w", err)
	}

	if len(config.Tools) == 0 {
		log.Error().
			Str("path", configPath).
			Msg("Tools configuration contains no tool definitions")
		return nil, fmt.Errorf("no tools defined in configuration")
	}

	return &config, nil
}

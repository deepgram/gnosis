package tools

import (
	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/logger"
	"github.com/deepgram/gnosis/internal/services/algolia"
	"github.com/deepgram/gnosis/internal/services/github"
	"github.com/deepgram/gnosis/internal/services/kapa"
	"github.com/sashabaranov/go-openai"
)

var configuredTools []openai.Tool

func InitializeTools() error {
	logger.Info("Initializing tools configuration")
	toolsConfig, err := config.LoadToolsConfig("config/tools.json")
	if err != nil {
		logger.Error("Failed to load tools config: %v", err)
		return err
	}

	var tools []openai.Tool
	for _, toolDef := range toolsConfig.Tools {
		// Only add tool if corresponding service is configured
		switch toolDef.Name {
		case "search_algolia":
			if !algolia.IsConfigured() {
				continue
			}
		case "search_starter_apps":
			if !github.IsConfigured() {
				continue
			}
		case "ask_kapa":
			if !kapa.IsConfigured() {
				continue
			}
		}

		tools = append(tools, openai.Tool{
			Type: "function",
			Function: &openai.FunctionDefinition{
				Name:        toolDef.Name,
				Description: toolDef.Description,
				Parameters:  toolDef.Parameters,
			},
		})
		logger.Info("Added tool: %s", toolDef.Name)
	}

	configuredTools = tools
	logger.Info("Finished loading tools - %d tools available", len(tools))
	return nil
}

func GetConfiguredTools() []openai.Tool {
	return configuredTools
}

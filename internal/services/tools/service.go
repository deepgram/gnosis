package tools

import (
	"sync"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/logger"
	"github.com/deepgram/gnosis/internal/services"
	"github.com/sashabaranov/go-openai"
)

var (
	configuredTools []openai.Tool
	toolsMu         sync.RWMutex
)

func InitializeTools() error {
	toolsMu.Lock()
	defer toolsMu.Unlock()
	logger.Info(logger.SERVICE, "Initializing tools configuration")
	toolsConfig, err := config.LoadToolsConfig("config/tools.json")
	if err != nil {
		logger.Error(logger.SERVICE, "Failed to load tools config: %v", err)
		return err
	}

	var tools []openai.Tool
	for _, toolDef := range toolsConfig.Tools {
		// Only add tool if corresponding service is configured
		switch toolDef.Name {
		case "search_algolia":
			if services.GetAlgoliaService() == nil {
				continue
			}
		case "search_starter_apps":
			if services.GetGitHubService() == nil {
				continue
			}
		case "ask_kapa":
			if services.GetKapaService() == nil {
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
		logger.Info(logger.SERVICE, "Added tool: %s", toolDef.Name)
	}

	configuredTools = tools
	logger.Info(logger.SERVICE, "Finished loading tools - %d tools available", len(tools))
	return nil
}

func GetConfiguredTools() []openai.Tool {
	toolsMu.RLock()
	defer toolsMu.RUnlock()
	return configuredTools
}

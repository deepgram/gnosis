package tools

import (
	"sync"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/logger"
	"github.com/deepgram/gnosis/internal/services/algolia"
	"github.com/deepgram/gnosis/internal/services/github"
	"github.com/deepgram/gnosis/internal/services/kapa"
	"github.com/sashabaranov/go-openai"
)

type Service struct {
	tools []openai.Tool
	mu    sync.RWMutex
}

func NewService(algoliaService *algolia.Service, githubService *github.Service, kapaService *kapa.Service) (*Service, error) {
	logger.Info(logger.SERVICE, "Initialising tools service")

	toolsConfig, err := config.LoadToolsConfig("config/tools.json")
	if err != nil {
		logger.Error(logger.SERVICE, "Failed to load tools config: %v", err)
		return nil, err
	}

	var tools []openai.Tool
	for _, toolDef := range toolsConfig.Tools {
		// Only add tool if corresponding service is configured
		switch toolDef.Name {
		case "search_algolia":
			if algoliaService == nil {
				continue
			}
		case "search_starter_apps":
			if githubService == nil {
				continue
			}
		case "ask_kapa":
			if kapaService == nil {
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

	logger.Info(logger.SERVICE, "Finished loading tools - %d tools available", len(tools))
	return &Service{
		tools: tools,
	}, nil
}

func (s *Service) GetTools() []openai.Tool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.tools
}

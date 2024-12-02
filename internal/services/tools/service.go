package tools

import (
	"sync"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/infrastructure/algolia"
	"github.com/deepgram/gnosis/internal/infrastructure/github"
	"github.com/deepgram/gnosis/internal/infrastructure/kapa"
	"github.com/sashabaranov/go-openai"
)

type Service struct {
	tools []openai.Tool
	mu    sync.RWMutex
}

func NewService(algoliaService *algolia.Service, githubService *github.Service, kapaService *kapa.Service) (*Service, error) {
	toolsConfig, err := config.LoadToolsConfig("internal/config/tools.json")
	if err != nil {
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
	}

	return &Service{
		tools: tools,
	}, nil
}

func (s *Service) GetTools() []openai.Tool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.tools
}

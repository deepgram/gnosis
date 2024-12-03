package tools

import (
	"encoding/json"
	"sync"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/infrastructure/algolia"
	"github.com/deepgram/gnosis/internal/infrastructure/github"
	"github.com/deepgram/gnosis/internal/infrastructure/kapa"
	"github.com/deepgram/gnosis/internal/services/tools/models"
	"github.com/sashabaranov/go-openai"

	"github.com/rs/zerolog/log"
)

type Service struct {
	tools          []openai.Tool
	mu             sync.RWMutex
	algoliaService *algolia.Service
	githubService  *github.Service
	kapaService    *kapa.Service
}

func NewService(algoliaService *algolia.Service, githubService *github.Service, kapaService *kapa.Service) *Service {
	toolsConfig, err := config.LoadToolsConfig("internal/config/tools.json")
	if err != nil {
		return nil
	}

	log.Debug().
		Interface("config", toolsConfig).
		Msg("Loading tools configuration")

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

		log.Debug().
			Str("tool_name", toolDef.Name).
			Msg("Evaluating tool configuration")

		tools = append(tools, openai.Tool{
			Type: "function",
			Function: &openai.FunctionDefinition{
				Name:        toolDef.Name,
				Description: toolDef.Description,
				Parameters:  toolDef.Parameters,
			},
		})
	}

	log.Debug().
		Int("enabled_tools", len(tools)).
		Msg("Tools service initialized with enabled integrations")

	return &Service{
		tools:          tools,
		algoliaService: algoliaService,
		githubService:  githubService,
		kapaService:    kapaService,
	}
}

// return all tools
func (s *Service) GetTools() []openai.Tool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.tools
}

// return functions in an openAI format
func (s *Service) GetOpenAITools() []openai.Tool {
	return s.GetTools()
}

/**
 * function maps tool format to deepgram format
 *
 * openai format:
 *	{
 *		"type": "function",
 *		"function": {
 *			"name": "get_weather",
 *			"parameters": {
 *				"type": "object",
 *				"properties": {
 *					"location": {"type": "string"},
 *					"unit": {"type": "string", "enum": ["c", "f"]},
 *				},
 *				"required": ["location", "unit"],
 *				"additionalProperties": false,
 *			},
 *		},
 *	}
 *
 * deepgram format:
 *	{
 *		"name": "", // function name
 *		"description": "", // tells the agent what the function does, and how and when to use it
 *		"parameters": {
 *			"type": "object",
 *			"properties": {
 *				"item": { // the name of the input property
 *					"type": "string", // the type of the input
 *					"description":"" // the description of the input so the agent understands what it is
 *				}
 *			},
 *			"required": ["item"] // the list of required input properties for this function to be called
 *		}
 *	}
 */
func (s *Service) GetDeepgramTools() []models.DeepgramToolCallConfig {
	var deepgramTools []models.DeepgramToolCallConfig
	for _, tool := range s.GetTools() {
		deepgramTools = append(deepgramTools, models.DeepgramToolCallConfig{
			Name:        tool.Function.Name,
			Description: tool.Function.Description,
			Parameters:  tool.Function.Parameters.(json.RawMessage),
		})
	}
	return deepgramTools
}

// return the tool executor
func (s *Service) GetToolExecutor() *ToolExecutor {
	return NewToolExecutor(s)
}

package chat

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/rs/zerolog/log"

	"github.com/deepgram/gnosis/internal/infrastructure/openai"
	chatModels "github.com/deepgram/gnosis/internal/services/chat/models"
	"github.com/deepgram/gnosis/internal/services/tools"
	"github.com/google/uuid"
	gopenai "github.com/sashabaranov/go-openai"
)

type Implementation struct {
	mu           sync.RWMutex
	openAI       *openai.Service
	toolService  *tools.Service
	systemPrompt *chatModels.SystemPrompt
}

func NewService(openAIService *openai.Service, toolService *tools.Service) (*Implementation, error) {
	if openAIService == nil {
		return nil, fmt.Errorf("OpenAI service is required")
	}

	log.Info().Msg("Initializing chat service")
	log.Debug().Msg("Setting up new chat service instance")

	log.Trace().
		Interface("openai_service", openAIService).
		Interface("tool_service", toolService).
		Msg("Constructing new chat service with dependencies")

	impl := &Implementation{
		openAI:       openAIService,
		toolService:  toolService,
		systemPrompt: chatModels.DefaultSystemPrompt(),
	}

	log.Trace().
		Str("system_prompt", chatModels.DefaultSystemPrompt().String()).
		Msg("Chat service initialized with default system prompt")

	return impl, nil
}

func (s *Implementation) ProcessChat(ctx context.Context, messages []chatModels.ChatMessage, config *chatModels.ChatConfig) (*chatModels.ChatResponse, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if len(messages) == 0 {
		return nil, fmt.Errorf("empty messages array")
	}

	// Check if first message is a system message
	if messages[0].Role == "system" {
		s.systemPrompt.SetCustom(messages[0].Content)
		messages = messages[1:]
		if len(messages) == 0 {
			return nil, fmt.Errorf("empty messages array after system prompt")
		}
	}

	// Convert domain messages to OpenAI messages
	openaiMessages := make([]gopenai.ChatCompletionMessage, len(messages)+1)
	openaiMessages[0] = gopenai.ChatCompletionMessage{
		Role:    gopenai.ChatMessageRoleSystem,
		Content: s.systemPrompt.String(),
	}
	for i, msg := range messages {
		openaiMessages[i+1] = gopenai.ChatCompletionMessage{
			Role:    msg.Role,
			Content: msg.Content,
		}
	}

	for {
		// Create completion request
		req := gopenai.ChatCompletionRequest{
			Model:            gopenai.GPT4oMini,
			Messages:         openaiMessages,
			Temperature:      config.Temperature,
			MaxTokens:        config.MaxTokens,
			TopP:             config.TopP,
			PresencePenalty:  config.PresencePenalty,
			FrequencyPenalty: config.FrequencyPenalty,
			Tools:            s.toolService.GetOpenAITools(),
		}

		log.Info().
			Int("message_count", len(messages)).
			Str("model", gopenai.GPT4oMini).
			Float32("temperature", config.Temperature).
			Msg("Processing chat request")

		log.Debug().
			Int("message_count", len(messages)).
			Interface("config", config).
			Msg("Processing new chat request")

		resp, err := s.openAI.GetClient().CreateChatCompletion(ctx, req)
		if err != nil {
			log.Error().Err(err).Msg("OpenAI API request failed")
			return nil, fmt.Errorf("chat completion failed: %w", err)
		}

		if len(resp.Choices) == 0 {
			return nil, fmt.Errorf("no response choices returned")
		}

		message := resp.Choices[0].Message

		// Return if we have a content response
		if message.Role == gopenai.ChatMessageRoleAssistant && message.Content != "" {
			response := &chatModels.ChatResponse{
				ID:      fmt.Sprintf("gnosis-%s", uuid.New().String()[:5]),
				Created: time.Now().Unix(),
				Choices: []chatModels.Choice{{
					Message: chatModels.ChatMessage{
						Role:    message.Role,
						Content: message.Content,
					},
				}},
				Usage: chatModels.Usage{
					PromptTokens:     resp.Usage.PromptTokens,
					CompletionTokens: resp.Usage.CompletionTokens,
					TotalTokens:      resp.Usage.TotalTokens,
				},
			}

			log.Info().
				Str("response_id", response.ID).
				Int("completion_tokens", response.Usage.CompletionTokens).
				Int("total_tokens", response.Usage.TotalTokens).
				Msg("Chat request processed successfully")

			return response, nil
		}

		// Handle tool calls
		if message.Role == gopenai.ChatMessageRoleAssistant && len(message.ToolCalls) > 0 {
			openaiMessages = append(openaiMessages, message)

			for _, toolCall := range message.ToolCalls {
				result, err := s.toolService.GetToolExecutor().ExecuteToolCall(ctx, toolCall)

				if err != nil {
					log.Error().
						Err(err).
						Str("tool", toolCall.Function.Name).
						Msg("Tool execution failed during chat completion")
					return nil, fmt.Errorf("tool call failed: %w", err)
				}

				openaiMessages = append(openaiMessages, gopenai.ChatCompletionMessage{
					Role:       gopenai.ChatMessageRoleTool,
					Content:    result,
					ToolCallID: toolCall.ID,
				})
			}
			continue
		}

		if message.Role != gopenai.ChatMessageRoleAssistant {
			log.Error().
				Str("role", string(message.Role)).
				Msg("Unexpected message role from OpenAI API")
			return nil, fmt.Errorf("unexpected message type from assistant")
		}

		return nil, fmt.Errorf("unexpected message type from assistant")
	}
}

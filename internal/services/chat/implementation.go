package chat

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/deepgram/gnosis/internal/infrastructure/openai"
	chatModels "github.com/deepgram/gnosis/internal/services/chat/models"
	"github.com/deepgram/gnosis/internal/services/tools"
	toolsModels "github.com/deepgram/gnosis/internal/services/tools/models"
	"github.com/deepgram/gnosis/pkg/logger"
	"github.com/google/uuid"
	gopenai "github.com/sashabaranov/go-openai"
)

type Implementation struct {
	mu           sync.RWMutex
	openAI       *openai.Service
	toolExecutor *tools.ToolExecutor
	systemPrompt *chatModels.SystemPrompt
}

func NewService(openAIService *openai.Service, toolExecutor *tools.ToolExecutor) (*Implementation, error) {
	if openAIService == nil {
		return nil, fmt.Errorf("OpenAI service is required")
	}

	return &Implementation{
		openAI:       openAIService,
		toolExecutor: toolExecutor,
		systemPrompt: chatModels.DefaultSystemPrompt(),
	}, nil
}

func (s *Implementation) ProcessChat(ctx context.Context, messages []chatModels.ChatMessage, config *chatModels.ChatConfig) (*chatModels.ChatResponse, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	logger.Debug(logger.CHAT, "Processing chat request with %d messages", len(messages))

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
			Model:            gopenai.GPT4Turbo,
			Messages:         openaiMessages,
			Temperature:      config.Temperature,
			MaxTokens:        config.MaxTokens,
			TopP:             config.TopP,
			PresencePenalty:  config.PresencePenalty,
			FrequencyPenalty: config.FrequencyPenalty,
		}

		resp, err := s.openAI.GetClient().CreateChatCompletion(ctx, req)
		if err != nil {
			logger.Error(logger.CHAT, "Failed to get chat completion: %v", err)
			return nil, fmt.Errorf("failed to get chat completion: %w", err)
		}

		if len(resp.Choices) == 0 {
			return nil, fmt.Errorf("no response choices returned")
		}

		message := resp.Choices[0].Message

		// Return if we have a content response
		if message.Role == gopenai.ChatMessageRoleAssistant && message.Content != "" {
			return &chatModels.ChatResponse{
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
			}, nil
		}

		// Handle tool calls
		if message.Role == gopenai.ChatMessageRoleAssistant && len(message.ToolCalls) > 0 {
			openaiMessages = append(openaiMessages, message)

			for _, toolCall := range message.ToolCalls {
				result, err := s.toolExecutor.ExecuteToolCall(ctx, toolsModels.ToolCall{
					ID:   toolCall.ID,
					Type: string(toolCall.Type),
					Function: struct {
						Name      string `json:"name"`
						Arguments string `json:"arguments"`
					}{
						Name:      toolCall.Function.Name,
						Arguments: toolCall.Function.Arguments,
					},
				})
				if err != nil {
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

		return nil, fmt.Errorf("unexpected message type from assistant")
	}
}

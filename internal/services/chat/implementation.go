package chat

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/deepgram/gnosis/internal/domain/chat"
	"github.com/deepgram/gnosis/internal/domain/chat/models"
	"github.com/deepgram/gnosis/internal/services/tools"
	"github.com/deepgram/gnosis/pkg/logger"
	"github.com/google/uuid"
	"github.com/sashabaranov/go-openai"
)

type Implementation struct {
	mu           sync.RWMutex
	client       *openai.Client
	toolExecutor *tools.ToolExecutor
	systemPrompt *models.SystemPrompt
}

func NewService(openAIKey string, toolExecutor *tools.ToolExecutor) (chat.Service, error) {
	if openAIKey == "" {
		return nil, fmt.Errorf("OpenAI key is required")
	}

	return &Implementation{
		client:       openai.NewClient(openAIKey),
		toolExecutor: toolExecutor,
		systemPrompt: models.DefaultSystemPrompt(),
	}, nil
}

func (s *Implementation) ProcessChat(ctx context.Context, messages []models.ChatMessage, config *models.ChatConfig) (*models.ChatResponse, error) {
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
	openaiMessages := make([]openai.ChatCompletionMessage, len(messages)+1)
	openaiMessages[0] = openai.ChatCompletionMessage{
		Role:    openai.ChatMessageRoleSystem,
		Content: s.systemPrompt.String(),
	}
	for i, msg := range messages {
		openaiMessages[i+1] = openai.ChatCompletionMessage{
			Role:    msg.Role,
			Content: msg.Content,
		}
	}

	for {
		// Create completion request
		req := openai.ChatCompletionRequest{
			Model:            openai.GPT4Turbo,
			Messages:         openaiMessages,
			Temperature:      config.Temperature,
			MaxTokens:        config.MaxTokens,
			TopP:             config.TopP,
			PresencePenalty:  config.PresencePenalty,
			FrequencyPenalty: config.FrequencyPenalty,
		}

		resp, err := s.client.CreateChatCompletion(ctx, req)
		if err != nil {
			logger.Error(logger.CHAT, "Failed to get chat completion: %v", err)
			return nil, fmt.Errorf("failed to get chat completion: %w", err)
		}

		if len(resp.Choices) == 0 {
			return nil, fmt.Errorf("no response choices returned")
		}

		message := resp.Choices[0].Message

		// Return if we have a content response
		if message.Role == openai.ChatMessageRoleAssistant && message.Content != "" {
			return &models.ChatResponse{
				ID:      fmt.Sprintf("gnosis-%s", uuid.New().String()[:5]),
				Created: time.Now().Unix(),
				Choices: []models.Choice{{
					Message: models.ChatMessage{
						Role:    message.Role,
						Content: message.Content,
					},
				}},
				Usage: models.Usage{
					PromptTokens:     resp.Usage.PromptTokens,
					CompletionTokens: resp.Usage.CompletionTokens,
					TotalTokens:      resp.Usage.TotalTokens,
				},
			}, nil
		}

		// Handle tool calls
		if message.Role == openai.ChatMessageRoleAssistant && len(message.ToolCalls) > 0 {
			openaiMessages = append(openaiMessages, message)

			for _, toolCall := range message.ToolCalls {
				result, err := s.toolExecutor.ExecuteToolCall(ctx, models.ToolCall{
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

				openaiMessages = append(openaiMessages, openai.ChatCompletionMessage{
					Role:       openai.ChatMessageRoleTool,
					Content:    result,
					ToolCallID: toolCall.ID,
				})
			}
			continue
		}

		return nil, fmt.Errorf("unexpected message type from assistant")
	}
}

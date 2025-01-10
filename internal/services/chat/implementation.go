package chat

import (
	"context"
	"fmt"
	"sync"

	"github.com/rs/zerolog/log"

	iopenai "github.com/deepgram/gnosis/internal/infrastructure/openai"
	chatModels "github.com/deepgram/gnosis/internal/services/chat/models"
	"github.com/deepgram/gnosis/internal/services/tools"
	"github.com/google/uuid"

	"github.com/sashabaranov/go-openai"
)

type Implementation struct {
	mu           sync.RWMutex
	openAI       *iopenai.Service
	toolService  *tools.Service
	systemPrompt *chatModels.SystemPrompt
}

func NewService(openAIService *iopenai.Service, toolService *tools.Service) (*Implementation, error) {
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

func (s *Implementation) ProcessChat(ctx context.Context, req openai.ChatCompletionRequest) (*openai.ChatCompletionResponse, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if len(req.Messages) == 0 {
		return nil, fmt.Errorf("empty messages array")
	}

	// Unsupported OpenAI features by Gnosis
	req.N = 1                     // We only ever want a single response
	req.Store = false             // We don't want to store the conversation history on OpenAI, but we may want to intercept this and store it ourselves
	req.MaxTokens = 0             // This is deprecated in favor of MaxCompletionTokens
	req.Stream = false            // TODO: We don't support streaming (yet), but we should prioritize adding this soon
	req.StreamOptions = nil       // We don't support streaming options
	req.ParallelToolCalls = false // TODO: We don't support parallel tool calls (yet), but we should prioritize adding this soon
	                              // Issue URL: https://github.com/deepgram/gnosis/issues/32
	req.FunctionCall = nil        // This is deprecated in favor of Tools
	req.Functions = nil           // This is deprecated in favor of Tools
	// req.ReasoningEffort = 0 // We don't support reasoning effort
	// req.Modalities = nil // We don't support modalities
	// req.Audio = nil // We don't support audio

	// Check if first message is a system message
	if req.Messages[0].Role == "system" {
		s.systemPrompt.SetCustom(req.Messages[0].Content)
		req.Messages = req.Messages[1:]
		if len(req.Messages) == 0 {
			return nil, fmt.Errorf("empty messages array after system prompt")
		}
	}

	// Convert domain messages to OpenAI messages
	openaiMessages := make([]openai.ChatCompletionMessage, len(req.Messages)+1)
	openaiMessages[0] = openai.ChatCompletionMessage{
		Role:    openai.ChatMessageRoleSystem,
		Content: s.systemPrompt.String(),
	}

	for i, msg := range req.Messages {
		openaiMessages[i+1] = openai.ChatCompletionMessage{
			Role:    msg.Role,
			Content: msg.Content,
		}
	}

	for {
		// Augment the OpenAI chat completion request
		req.Messages = openaiMessages
		req.Tools = s.toolService.GetOpenAITools()

		log.Info().
			Int("message_count", len(req.Messages)).
			Str("model", req.Model).
			Float32("temperature", req.Temperature).
			Msg("Processing chat request")

		log.Debug().
			Int("message_count", len(req.Messages)).
			Interface("config", req).
			Msg("Processing new chat request")

		response, err := s.openAI.GetClient().CreateChatCompletion(ctx, req)
		if err != nil {
			log.Error().Err(err).Msg("OpenAI API request failed")
			return nil, fmt.Errorf("chat completion failed: %w", err)
		}

		if len(response.Choices) == 0 {
			return nil, fmt.Errorf("no response choices returned")
		}

		// Return if we have a content response
		if response.Choices[0].Message.Role == openai.ChatMessageRoleAssistant && response.Choices[0].Message.Content != "" {
			response.ID = fmt.Sprintf("gnosis-%s", uuid.New().String()[:5])

			log.Info().
				Str("response_id", response.ID).
				Int("completion_tokens", response.Usage.CompletionTokens).
				Int("total_tokens", response.Usage.TotalTokens).
				Msg("Chat request processed successfully")

			return &response, nil
		}

		// Handle tool calls
		if response.Choices[0].Message.Role == openai.ChatMessageRoleAssistant && len(response.Choices[0].Message.ToolCalls) > 0 {
			openaiMessages = append(openaiMessages, response.Choices[0].Message)

			for _, toolCall := range response.Choices[0].Message.ToolCalls {
				result, err := s.toolService.GetToolExecutor().ExecuteToolCall(ctx, toolCall)

				if err != nil {
					log.Error().
						Err(err).
						Str("tool", toolCall.Function.Name).
						Msg("Tool execution failed during chat completion")
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

		if response.Choices[0].Message.Role != openai.ChatMessageRoleAssistant {
			log.Error().
				Str("role", string(response.Choices[0].Message.Role)).
				Msg("Unexpected message role from OpenAI API")
			return nil, fmt.Errorf("unexpected message type from assistant")
		}

		return nil, fmt.Errorf("unexpected message type from assistant")
	}
}

package chat

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"time"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/logger"
	"github.com/deepgram/gnosis/internal/services/algolia"
	"github.com/deepgram/gnosis/internal/services/github"
	"github.com/deepgram/gnosis/internal/services/kapa"
	"github.com/deepgram/gnosis/internal/services/tools"
	"github.com/google/uuid"
	"github.com/sashabaranov/go-openai"
)

const systemPrompt = `
Provide the most helpful response to Deepgram users' community questions. Assume all inquiries are about Deepgram or how you were built.

Communicate these Deepgram service differences clearly:
- 'https://api.deepgram.com/v1/listen': Transcription / Speech-to-text (STT) / Automatic Speech Recognition (ASR)
- 'wss://api.deepgram.com/v1/listen': Live Transcription / Live Speech-to-text (STT) / Live Automatic Speech Recognition (ASR)
- 'https://api.deepgram.com/v1/read': Text Intelligence
- 'https://api.deepgram.com/v1/speak': Text-to-speech (TTS)
- 'wss://api.deepgram.com/v1/speak': Live Text-to-speech (TTS)
- 'wss://api.deepgram.com/v1/agent': Voice Agent / Speech-to-speech (S2S) / Live Speech-to-speech (S2S)

## Request handling
- If the question is asked in a language other than English, translate it to English before using the tools.
- If someone asks for the cost of any product, use 'search_algolia' for "pricing" specifically.
- Only use tool calls if the data isn't already present in the chat history.

## Response handling
- Always respond in the same language as the question.
- Keep answers concise and to the point
- Don't provide code examples unless explicitly asked for.
- When code examples are available, ask them if they'd like to see one.
- When asking for code examples, ask which programming language they'd like to see an example in.
`

type Service struct {
	openaiClient   *openai.Client
	algoliaService *algolia.Service
	githubService  *github.Service
	kapaService    *kapa.Service
	toolsService   *tools.Service
}

func NewService(algoliaService *algolia.Service, githubService *github.Service, kapaService *kapa.Service, toolsService *tools.Service) *Service {
	logger.Info(logger.SERVICE, "Initializing chat service")
	client := openai.NewClient(config.GetOpenAIKey())
	logger.Debug(logger.SERVICE, "OpenAI client initialized")
	return &Service{
		openaiClient:   client,
		algoliaService: algoliaService,
		githubService:  githubService,
		kapaService:    kapaService,
		toolsService:   toolsService,
	}
}

type ChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type ChatResponse struct {
	ID      string   `json:"id"`
	Created int64    `json:"created"`
	Choices []Choice `json:"choices"`
	Usage   Usage    `json:"usage"`
}

type Choice struct {
	Message ChatMessage `json:"message"`
}

type Usage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// Add new types for request configuration
type ChatConfig struct {
	Temperature      float32 `json:"temperature,omitempty"`
	MaxTokens        int     `json:"max_tokens,omitempty"`
	TopP             float32 `json:"top_p,omitempty"`
	PresencePenalty  float32 `json:"presence_penalty,omitempty"`
	FrequencyPenalty float32 `json:"frequency_penalty,omitempty"`
}

// Update ProcessChat to accept config
func (s *Service) ProcessChat(ctx context.Context, messages []ChatMessage, config *ChatConfig) (*ChatResponse, error) {
	logger.Info(logger.SERVICE, "Starting chat processing")
	logger.Debug(logger.SERVICE, "Processing %d messages with model: %s", len(messages), "gpt-4o-mini")

	if len(messages) == 0 {
		logger.Warn(logger.SERVICE, "Received empty messages array for chat processing")
		return nil, fmt.Errorf("empty messages array")
	}

	// Convert our ChatMessage type to OpenAI's type
	openaiMessages := make([]openai.ChatCompletionMessage, len(messages))
	for i, msg := range messages {
		openaiMessages[i] = openai.ChatCompletionMessage{
			Role:    msg.Role,
			Content: msg.Content,
		}
	}

	req := s.buildChatRequest(openaiMessages, config)
	logger.Debug(logger.SERVICE, "Built chat request with model: %s", "gpt-4o-mini")

	for {
		logger.Debug(logger.SERVICE, "Making request to OpenAI")
		resp, err := s.openaiClient.CreateChatCompletion(ctx, req)
		if err != nil {
			logger.Error(logger.SERVICE, "OpenAI request failed: %v", err)
			return nil, fmt.Errorf("openai request failed: %w", err)
		}

		if len(resp.Choices) == 0 {
			logger.Error(logger.SERVICE, "No response choices returned from OpenAI")
			return nil, fmt.Errorf("no response choices returned")
		}

		message := resp.Choices[0].Message
		logger.Debug(logger.SERVICE, "Received message - Role: %s, Content length: %d",
			message.Role, len(message.Content))

		// Return if we have a content response
		if message.Role == openai.ChatMessageRoleAssistant && message.Content != "" {
			logger.Debug(logger.SERVICE, "Returning content response of length: %d", len(message.Content))

			return &ChatResponse{
				ID:      fmt.Sprintf("gnosis-%s", uuid.New().String()[:5]),
				Created: time.Now().Unix(),
				Choices: []Choice{
					{
						Message: ChatMessage{
							Role:    message.Role,
							Content: message.Content,
						},
					},
				},
				Usage: Usage{
					PromptTokens:     resp.Usage.PromptTokens,
					CompletionTokens: resp.Usage.CompletionTokens,
					TotalTokens:      resp.Usage.TotalTokens,
				},
			}, nil
		}

		// Handle tool calls
		if message.Role == openai.ChatMessageRoleAssistant && len(message.ToolCalls) > 0 {
			logger.Debug(logger.SERVICE, "Processing %d tool calls", len(message.ToolCalls))
			// Add the assistant's message with tool calls
			req.Messages = append(req.Messages, message)

			// Process each tool call
			for _, tool := range message.ToolCalls {
				result, err := s.executeToolCall(ctx, tool)
				if err != nil {
					return nil, fmt.Errorf("tool call failed: %w", err)
				}

				// Add the tool response
				req.Messages = append(req.Messages, openai.ChatCompletionMessage{
					Role:       openai.ChatMessageRoleTool,
					Content:    result,
					ToolCallID: tool.ID,
				})
			}
			continue
		}

		return nil, fmt.Errorf("unexpected message type from assistant")
	}
}

// Update buildChatRequest to use config
func (s *Service) buildChatRequest(messages []openai.ChatCompletionMessage, config *ChatConfig) openai.ChatCompletionRequest {
	// Set default values if not provided
	model := "gpt-4o-mini"

	req := openai.ChatCompletionRequest{
		Model: model,
		Messages: append([]openai.ChatCompletionMessage{{
			Role:    openai.ChatMessageRoleSystem,
			Content: systemPrompt,
		}}, messages...),
		Tools: s.toolsService.GetTools(),
	}

	// Apply optional configurations if provided
	if config != nil {
		if config.Temperature > 0 {
			req.Temperature = float32(config.Temperature)
		}
		if config.MaxTokens > 0 {
			req.MaxTokens = config.MaxTokens
		}
		if config.TopP > 0 {
			req.TopP = float32(config.TopP)
		}
		if config.PresencePenalty != 0 {
			req.PresencePenalty = float32(config.PresencePenalty)
		}
		if config.FrequencyPenalty != 0 {
			req.FrequencyPenalty = float32(config.FrequencyPenalty)
		}
	}

	// Pretty print the request object as JSON for debugging
	if jsonBytes, err := json.MarshalIndent(req, "", "  "); err == nil {
		logger.Debug(logger.SERVICE, "OpenAI request:\n%s", string(jsonBytes))
	} else {
		logger.Error(logger.SERVICE, "Failed to marshal OpenAI request for debugging: %v", err)
	}

	return req
}

func (s *Service) executeToolCall(ctx context.Context, tool openai.ToolCall) (string, error) {
	logger.Info("Executing tool call: %s", tool.Function.Name)
	if tool.Type != "function" {
		return "", fmt.Errorf("unsupported tool type")
	}

	switch tool.Function.Name {
	case "search_algolia":
		var params struct {
			Query string `json:"query"`
		}
		if err := json.Unmarshal([]byte(tool.Function.Arguments), &params); err != nil {
			logger.Error(logger.SERVICE, "Failed to parse search parameters: %v", err)
			return "", fmt.Errorf("invalid parameters: %v", err)
		}

		result, err := s.algoliaService.Search(ctx, params.Query)
		if err != nil {
			return "", fmt.Errorf("algolia search failed: %w", err)
		}

		if len(result.Hits) == 0 {
			return "No relevant documentation found.", nil
		}

		hit := result.Hits[0]
		response := fmt.Sprintf("Found relevant documentation:\n\nTitle: %s\n\n%s\n\nSource: %s",
			hit.Title,
			hit.Content,
			hit.URL)

		logger.Debug(logger.SERVICE, "Algolia search response: %s", response)
		logger.Info(logger.SERVICE, "Algolia search result found")

		return response, nil

	case "search_starter_apps":
		var params struct {
			Topics   []string `json:"topics"`
			Language string   `json:"language"`
		}
		if err := json.Unmarshal([]byte(tool.Function.Arguments), &params); err != nil {
			return "", fmt.Errorf("invalid parameters: %v", err)
		}

		searchResult, err := s.githubService.SearchRepos(ctx, "deepgram-starters", params.Language, params.Topics)
		if err != nil {
			return "", fmt.Errorf("github search failed: %w", err)
		}

		if len(searchResult.Items) == 0 {
			return "No relevant code samples found.", nil
		}

		// Get the first repo (should be the most relevant)
		repo := searchResult.Items[0]

		// Get the README for the repo
		readmeResult, err := s.githubService.GetRepoReadme(ctx, repo.FullName)
		if err != nil {
			return "", fmt.Errorf("github readme failed: %w", err)
		}

		readmeContents, err := base64.StdEncoding.DecodeString(readmeResult.Content)
		if err != nil {
			return "", fmt.Errorf("unable to decode contents: %w", err)
		}

		response := fmt.Sprintf("Found relevant starter app:\n\nRepo: %s\nDescription: %s\nInstructions to use:\n%s",
			repo.HTMLURL,
			repo.Description,
			string(readmeContents),
		)

		logger.Info("Starter app search response: %s", response)

		// Return a markdown response
		return response, nil

	case "ask_kapa":
		var params struct {
			Question string   `json:"question"`
			Product  string   `json:"product"`
			Tags     []string `json:"tags"`
		}

		if err := json.Unmarshal([]byte(tool.Function.Arguments), &params); err != nil {
			return "", fmt.Errorf("invalid parameters: %v", err)
		}

		resp, err := s.kapaService.Query(ctx, params.Question, params.Product, params.Tags)
		if err != nil {
			return "", fmt.Errorf("kapa query failed: %w", err)
		}

		return resp.Answer, nil

	default:
		return "", fmt.Errorf("unknown function: %s", tool.Function.Name)
	}
}

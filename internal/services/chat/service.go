package chat

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"time"

	"github.com/deepgram/codename-sage/internal/config"
	"github.com/deepgram/codename-sage/internal/logger"
	"github.com/deepgram/codename-sage/internal/services/algolia"
	"github.com/deepgram/codename-sage/internal/services/github"
	"github.com/deepgram/codename-sage/internal/services/kapa"
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

## Response handling
- Always respond in the same language as the question.
- Keep answers concise and to the point
- Don't provide code examples unless explicitly asked for.
- When code examples are available, ask them if they'd like to see one.
- When asking for code examples, ask which programming language they'd like to see an example in.
`

type Service struct {
	openaiClient *openai.Client
}

func NewService() *Service {
	logger.Info("Initializing chat service")
	client := openai.NewClient(config.GetOpenAIKey())
	logger.Debug("OpenAI client initialized")
	return &Service{
		openaiClient: client,
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
	logger.Info("Starting chat processing")
	logger.Debug("Processing %d messages with model: %s", len(messages), "gpt-4o-mini")

	if len(messages) == 0 {
		logger.Warn("Received empty messages array for chat processing")
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
	logger.Debug("Built chat request with model: %s", "gpt-4o-mini")

	for {
		logger.Debug("Making request to OpenAI")
		resp, err := s.openaiClient.CreateChatCompletion(ctx, req)
		if err != nil {
			logger.Error("OpenAI request failed: %v", err)
			return nil, fmt.Errorf("openai request failed: %w", err)
		}

		if len(resp.Choices) == 0 {
			logger.Error("No response choices returned from OpenAI")
			return nil, fmt.Errorf("no response choices returned")
		}

		message := resp.Choices[0].Message
		logger.Debug("Received message - Role: %s, Content length: %d, Tool calls: %d",
			message.Role, len(message.Content), len(message.ToolCalls))

		// Return if we have a content response
		if message.Role == openai.ChatMessageRoleAssistant && message.Content != "" {
			logger.Debug("Returning content response of length: %d", len(message.Content))

			return &ChatResponse{
				ID:      fmt.Sprintf("sage-%s", uuid.New().String()[:8]),
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
			logger.Debug("Processing %d tool calls", len(message.ToolCalls))
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
		Tools: s.getTools(), // Move tools to separate function for clarity
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

	return req
}

// Move tools to separate function for cleaner code
func (s *Service) getTools() []openai.Tool {
	return []openai.Tool{
		{
			Type: "function",
			Function: &openai.FunctionDefinition{
				Name:        "search_algolia",
				Description: "Search for additional product information like pricing, tutorials, and documentation",
				Strict:      true,
				Parameters: map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"query": map[string]interface{}{
							"type":        "string",
							"description": "Search term or phrase to find relevant results",
						},
					},
					"required":             []string{"query"},
					"additionalProperties": false,
				},
			},
		},
		{
			Type: "function",
			Function: &openai.FunctionDefinition{
				Name:        "search_starter_apps",
				Description: "Search by language and topic for a getting started app",
				Strict:      true,
				Parameters: map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"topics": map[string]interface{}{
							"type":        "array",
							"description": "The topics to search for",
							"items": map[string]interface{}{
								"type":        "string",
								"enum":        []string{"live", "speech-to-text", "text-intelligence", "text-to-speech", "voice-agent"},
								"description": "The topic to search for",
							},
						},
						"language": map[string]interface{}{
							"type":        "string",
							"enum":        []string{"python", "javascript", "java", "csharp", "go", "ruby", "php", "swift", "kotlin", "rust", "typescript", "c", "c++", "objective-c"},
							"description": "The programming language of the code samples to retrieve",
						},
					},
					"required":             []string{"topics", "language"},
					"additionalProperties": false,
				},
			},
		},
		{
			Type: "function",
			Function: &openai.FunctionDefinition{
				Name:        "ask_kapa",
				Description: "Search for answers to technical questions about a product",
				Strict:      true,
				Parameters: map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"question": map[string]interface{}{
							"type":        "string",
							"description": "Summary of the technical question to answer about a product",
						},
						"product": map[string]interface{}{
							"type":        "string",
							"description": "The product the question is about",
							"enum":        []string{"speech-to-text", "text-intelligence", "text-to-speech", "voice-agent"},
						},
						"tags": map[string]interface{}{
							"type":        "array",
							"description": "Relevant tags to categorize the question",
							"items": map[string]interface{}{
								"type":        "string",
								"enum":        []string{"general", "technical", "billing", "account", "security", "api", "sdk", "tool", "other"},
								"description": "Tag for categorizing the question",
							},
						},
					},
					"required":             []string{"question", "product", "tags"},
					"additionalProperties": false,
				},
			},
		},
	}
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
			logger.Error("Failed to parse search parameters: %v", err)
			return "", fmt.Errorf("invalid parameters: %v", err)
		}

		algoliaService := algolia.NewService()
		result, err := algoliaService.Search(ctx, params.Query)
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

		logger.Info("Algolia search response: %s", response)

		return response, nil

	case "search_starter_apps":
		var params struct {
			Topics   []string `json:"topics"`
			Language string   `json:"language"`
		}
		if err := json.Unmarshal([]byte(tool.Function.Arguments), &params); err != nil {
			return "", fmt.Errorf("invalid parameters: %v", err)
		}

		githubService := github.NewService()
		searchResult, err := githubService.SearchRepos(ctx, "deepgram-starters", params.Language, params.Topics)
		if err != nil {
			return "", fmt.Errorf("github search failed: %w", err)
		}

		if len(searchResult.Items) == 0 {
			return "No relevant code samples found.", nil
		}

		// Get the first repo (should be the most relevant)
		repo := searchResult.Items[0]

		// Get the README for the repo
		readmeResult, err := githubService.GetRepoReadme(ctx, repo.FullName)
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

		// Unmarshal the parameters
		if err := json.Unmarshal([]byte(tool.Function.Arguments), &params); err != nil {
			return "", fmt.Errorf("invalid parameters: %v", err)
		}

		// Initialize Kapa service
		kapaService := kapa.NewService()

		// Query Kapa
		resp, err := kapaService.Query(ctx, params.Question, params.Product, params.Tags)
		if err != nil {
			return "", fmt.Errorf("kapa query failed: %w", err)
		}

		// Return the answer
		return resp.Answer, nil

	default:
		return "", fmt.Errorf("unknown function: %s", tool.Function.Name)
	}
}

package chat

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/deepgram/codename-sage/internal/config"
	"github.com/deepgram/codename-sage/internal/logger"
	"github.com/deepgram/codename-sage/internal/services/algolia"
	"github.com/deepgram/codename-sage/internal/services/kapa"
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
	client := openai.NewClient(string(config.GetOpenAIKey()))
	logger.Debug("OpenAI client initialized")
	return &Service{
		openaiClient: client,
	}
}

func (s *Service) ProcessChat(ctx context.Context, messages []openai.ChatCompletionMessage) (*openai.ChatCompletionMessage, error) {
	logger.Info("Processing chat request with %d messages", len(messages))
	if len(messages) == 0 {
		logger.Warn("Received empty messages array for chat processing")
		return nil, fmt.Errorf("empty messages array")
	}

	// Add warning for large message arrays
	if len(messages) > 50 {
		logger.Warn("Large message array received: %d messages", len(messages))
	}

	req := s.buildChatRequest(messages)

	for {
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

		// Return if we have a content response
		if message.Role == openai.ChatMessageRoleAssistant && message.Content != "" {
			return &message, nil
		}

		// Handle tool calls
		if message.Role == openai.ChatMessageRoleAssistant && len(message.ToolCalls) > 0 {
			logger.Info("Processing %d tool calls", len(message.ToolCalls))
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

func (s *Service) buildChatRequest(messages []openai.ChatCompletionMessage) openai.ChatCompletionRequest {
	return openai.ChatCompletionRequest{
		Model: "gpt-4",
		Messages: append([]openai.ChatCompletionMessage{{
			Role:    openai.ChatMessageRoleSystem,
			Content: systemPrompt,
		}}, messages...),
		Tools: []openai.Tool{
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
					Name:        "search_code_samples",
					Description: "Search for code samples for a specific programming language",
					Strict:      true,
					Parameters: map[string]interface{}{
						"type": "object",
						"properties": map[string]interface{}{
							"query": map[string]interface{}{
								"type":        "string",
								"description": "Search term or phrase to find relevant code samples",
							},
							"language": map[string]interface{}{
								"type":        "string",
								"enum":        []string{"python", "javascript", "java", "csharp", "go", "ruby", "php", "swift", "kotlin", "rust", "typescript", "c", "c++", "objective-c"},
								"description": "The programming language of the code samples to retrieve",
							},
						},
						"required":             []string{"query", "language"},
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
								"enum":        []string{"speech-to-text", "text-intelligence", "text-to-speech", ""},
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

	case "search_code_samples":
		var params struct {
			Query    string `json:"query"`
			Language string `json:"language"`
		}
		if err := json.Unmarshal([]byte(tool.Function.Arguments), &params); err != nil {
			return "", fmt.Errorf("invalid parameters: %v", err)
		}
		// TODO: Implement code samples search
		return "Here's a code sample: ```python\nprint('Hello, world!')\n```", nil

	case "search_starter_apps":
		var params struct {
			Query    string `json:"query"`
			Language string `json:"language"`
		}
		if err := json.Unmarshal([]byte(tool.Function.Arguments), &params); err != nil {
			return "", fmt.Errorf("invalid parameters: %v", err)
		}
		// TODO: Implement code samples search
		return "Here's a code sample: ```python\nprint('Hello, world!')\n```", nil
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

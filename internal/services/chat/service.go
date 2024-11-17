package chat

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/deepgram/navi/internal/config"
	"github.com/deepgram/navi/internal/logger"
	"github.com/deepgram/navi/internal/services/kapa"
	"github.com/sashabaranov/go-openai"
)

const systemPrompt = `
You're an AI assistant helping our users answer their own community questions about the Deepgram service. Any questions should be assumed to be related to Deepgram or about how you yourself have been built.

# Task Description
Assist users by providing helpful, insightful responses that guide them towards finding their own answers for community-related queries. Ensure that you only provide the most up-to-date information available. If you don't know the answer, ensure you call functions to fetch the latest data, and never refer to outdated data.

Your functions include:
- **search_algolia**: Use this function if someone asks about a specific Deepgram service, pricing, or feature.
- **search_code_samples**: Use this function if someone asks about how to use a specific Deepgram service in a particular programming language.
- **search_community_articles**: Use this function if someone asks a question that may have already been answered in the community.
- **ask_kapa**: Use this function if someone asks a question that is not answered by the other tools.

If the relevant data you have is outdated or if no conclusive response is obtained from function calls, perform the following actions in order of priority:
1. Provide a link to the best-known page that could potentially provide the correct answer.
2. If no suitable link is available, advise the user to raise the question in the community forum.
3. If the user is on a support plan, recommend that they contact their Deepgram representative.

Additionally, understand the following distinctions for different Deepgram services:
- If the user mentions 'https://api.deepgram.com/v1/listen', it refers to the REST API for transcription. If a callback URL is provided, it means the request is asynchronous, and Deepgram will send the transcribed information to the URL in the callback parameter.
- If the user mentions 'wss://api.deepgram.com/v1/listen', it refers to the live transcription websocket. A callback URL can also be used here.
- If the user mentions 'https://api.deepgram.com/v1/read', it indicates they are using the Text Intelligence service.
- If the user mentions 'https://api.deepgram.com/v1/speak', it is referring to the REST text-to-speech service.
- If the user mentions 'wss://api.deepgram.com/v1/speak', it is referring to the text-to-speech service provided via websocket.

Ensure that these distinctions are communicated clearly when assisting users with questions about specific Deepgram services.

# Output Format
Provide clear and concise answers, guiding users effectively either to direct links, community forums, or support assistance based on the situation. Always include one of the following follow-up options:
- A link to a relevant webpage, if available.
- An invitation to speak to their Deepgram representative (if they have a support contract).
- An invitation to join our community at https://discord.gg/deepgram and ask for more help there.

# Example Function Calls
You may use the following functions for fetching information:
- **search_algolia(query)**: to fetch results from the Deepgram website. Example: 'search_algolia("transcription API documentation")'
- **search_code_samples(query)**: to find relevant AI-generated code examples. Example: 'search_code_samples("websocket transcription example")'
- **search_community_articles(query)**: to retrieve helpful community-driven Q&A. Example: 'search_community_articles("handling callback URLs")'
- **ask_kapa(query)**: to get a suggested answer from Kapa. Example: 'ask_kapa("how to use live transcription websocket")'

# Examples

### Example 1:
Input: "How can I use https://api.deepgram.com/v1/listen for my project?"
Output: "The endpoint 'https://api.deepgram.com/v1/listen' is used for REST API transcription. If you provide a 'callback' parameter, the request will be asynchronous, and Deepgram will send the response to the callback URL. For more details on using this endpoint, you can visit [link to documentation]. If you need more assistance, consider discussing it with your Deepgram representative or join our community at https://discord.gg/deepgram for help from other users."

### Example 2:
Input: "Is wss://api.deepgram.com/v1/listen suitable for real-time transcription?"
Output: "The 'wss://api.deepgram.com/v1/listen' endpoint is designed for real-time transcription using a websocket connection. You can also use a callback URL here for asynchronous processing if needed. For more live transcription details, you can view our guide at [link to documentation]. If you have further questions, please speak to your Deepgram representative, or join our community at https://discord.gg/deepgram."

### Example 3:
Input: "What does https://api.deepgram.com/v1/read do?"
Output: "The endpoint 'https://api.deepgram.com/v1/read' is used for accessing Deepgram's Text Intelligence service. More details on how to leverage Text Intelligence can be found at [link to documentation]. Additionally, you can try 'search_algolia('text intelligence')' for further relevant resources. Feel free to contact your Deepgram representative or join our Discord community (https://discord.gg/deepgram) if you need further support."

### Example 4:
Input: "How do I use https://api.deepgram.com/v1/speak for text-to-speech?"
Output: "The 'https://api.deepgram.com/v1/speak' endpoint is used for the REST text-to-speech service. You can send text to this endpoint, and it will return the corresponding speech output. For more information, you could refer to [link to documentation] or call 'search_code_samples('text to speech API')' for example code snippets. For any additional queries, reach out to your Deepgram representative or head over to our community on Discord (https://discord.gg/deepgram)."

### Example 5:
Input: "Can I use wss://api.deepgram.com/v1/speak for generating speech?"
Output: "The 'wss://api.deepgram.com/v1/speak' endpoint is used for text-to-speech using a websocket connection. This allows for real-time generation of speech from text. You can check the specific guide for WebSocket text-to-speech at [link to documentation]. If needed, 'search_algolia' can be used to find more related guides and details. You can also join our community at https://discord.gg/deepgram for more help, or speak with your customer representative."

# Notes
- Use relevant functions ('search_algolia', 'search_code_samples', 'search_community_articles', 'ask_kapa') to ensure that information provided is as current as possible.
- Make sure to differentiate between real-time and asynchronous requests when users mention callback URLs.
- Refer users to appropriate resources whenever possible to ensure they receive the most helpful and recent information.
- Clearly distinguish between the REST and WebSocket versions of both transcription and text-to-speech services.
- Always follow up by suggesting either joining the community on Discord, contacting their Deepgram representative (if applicable), or providing a useful documentation link.
- You can always use more than one tool call in a single response if needed.
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
					Description: "Use this function if someone asks about a specific Deepgram service, pricing, or feature.",
					Strict:      true,
					Parameters: map[string]interface{}{
						"type": "object",
						"properties": map[string]interface{}{
							"query": map[string]interface{}{
								"type":        "string",
								"description": "The search term provided by the user",
							},
							"filters": map[string]interface{}{
								"type":        "string",
								"description": "Additional filters to apply to the search",
							},
						},
						"required":             []string{"query", "filters"},
						"additionalProperties": false,
					},
				},
			},
			{
				Type: "function",
				Function: &openai.FunctionDefinition{
					Name:        "search_code_samples",
					Description: "Use this function if someone asks about how to use a specific Deepgram service in a particular programming language.",
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
								"description": "The programming language of the code samples to retrieve",
							},
							"limit": map[string]interface{}{
								"type":        "number",
								"description": "The maximum number of code samples to return",
							},
							"context": map[string]interface{}{
								"type":        "string",
								"description": "Additional context or specifications for the code samples search",
							},
						},
						"required":             []string{"query", "language", "limit", "context"},
						"additionalProperties": false,
					},
				},
			},
			{
				Type: "function",
				Function: &openai.FunctionDefinition{
					Name:        "search_community_articles",
					Description: "Use this function if someone asks a question that may have already been answered in the community.",
					Strict:      true,
					Parameters: map[string]interface{}{
						"type": "object",
						"properties": map[string]interface{}{
							"query": map[string]interface{}{
								"type":        "string",
								"description": "Search term or phrase to look for in community articles",
							},
							"category": map[string]interface{}{
								"type":        "string",
								"description": "The category of articles to search in",
							},
							"limit": map[string]interface{}{
								"type":        "number",
								"description": "Maximum number of articles to return",
							},
							"offset": map[string]interface{}{
								"type":        "number",
								"description": "Number of articles to skip before starting to collect the result set",
							},
						},
						"required":             []string{"query", "category", "limit", "offset"},
						"additionalProperties": false,
					},
				},
			},
			{
				Type: "function",
				Function: &openai.FunctionDefinition{
					Name:        "ask_kapa",
					Description: "Use this function if someone asks a question that is not answered by the other tools.",
					Strict:      true,
					Parameters: map[string]interface{}{
						"type": "object",
						"properties": map[string]interface{}{
							"question": map[string]interface{}{
								"type":        "string",
								"description": "The question for which assistance is requested",
							},
							"context": map[string]interface{}{
								"type":        "string",
								"description": "Additional context or details to improve the quality of the answer",
							},
							"tags": map[string]interface{}{
								"type":        "array",
								"description": "Relevant tags to categorize the question",
								"items": map[string]interface{}{
									"type":        "string",
									"description": "Tag for categorizing the question",
								},
							},
						},
						"required":             []string{"question", "context", "tags"},
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
			Query   string `json:"query"`
			Filters string `json:"filters"`
		}
		if err := json.Unmarshal([]byte(tool.Function.Arguments), &params); err != nil {
			logger.Error("Failed to parse search parameters: %v", err)
			return "", fmt.Errorf("invalid parameters: %v", err)
		}
		// TODO: Implement actual Algolia search
		return "Here's a link to the Deepgram website: https://www.deepgram.com", nil

	case "search_code_samples":
		var params struct {
			Query    string  `json:"query"`
			Language string  `json:"language"`
			Limit    float64 `json:"limit"`
			Context  string  `json:"context"`
		}
		if err := json.Unmarshal([]byte(tool.Function.Arguments), &params); err != nil {
			return "", fmt.Errorf("invalid parameters: %v", err)
		}
		// TODO: Implement code samples search
		return "Here's a code sample: ```python\nprint('Hello, world!')\n```", nil

	case "search_community_articles":
		var params struct {
			Query    string  `json:"query"`
			Category string  `json:"category"`
			Limit    float64 `json:"limit"`
			Offset   float64 `json:"offset"`
		}
		if err := json.Unmarshal([]byte(tool.Function.Arguments), &params); err != nil {
			return "", fmt.Errorf("invalid parameters: %v", err)
		}
		// TODO: Implement community articles search
		return "The answer is 42.", nil

	case "ask_kapa":
		var params struct {
			Question string   `json:"question"`
			Context  string   `json:"context"`
			Tags     []string `json:"tags"`
		}

		// Unmarshal the parameters
		if err := json.Unmarshal([]byte(tool.Function.Arguments), &params); err != nil {
			return "", fmt.Errorf("invalid parameters: %v", err)
		}

		// Initialize Kapa service
		kapaService := kapa.NewService()

		// Query Kapa
		resp, err := kapaService.Query(ctx, params.Question, params.Context, params.Tags)
		if err != nil {
			return "", fmt.Errorf("kapa query failed: %w", err)
		}

		// Return the answer
		return resp.Answer, nil
	default:
		return "", fmt.Errorf("unknown function: %s", tool.Function.Name)
	}
}

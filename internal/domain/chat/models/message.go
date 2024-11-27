package models

// ChatMessage represents a single message in a chat conversation
type ChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// ChatConfig represents configuration options for chat processing
type ChatConfig struct {
	Temperature      float32 `json:"temperature,omitempty"`
	MaxTokens        int     `json:"max_tokens,omitempty"`
	TopP             float32 `json:"top_p,omitempty"`
	PresencePenalty  float32 `json:"presence_penalty,omitempty"`
	FrequencyPenalty float32 `json:"frequency_penalty,omitempty"`
}

// ChatResponse represents the response from a chat completion
type ChatResponse struct {
	ID      string   `json:"id"`
	Created int64    `json:"created"`
	Choices []Choice `json:"choices"`
	Usage   Usage    `json:"usage"`
}

// Choice represents a single chat completion choice
type Choice struct {
	Message ChatMessage `json:"message"`
}

// Usage represents token usage information
type Usage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

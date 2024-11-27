package models

import "context"

// ToolExecutor defines the interface for executing tool calls
type ToolExecutor interface {
	ExecuteToolCall(ctx context.Context, call ToolCall) (string, error)
}

// ToolCall represents a request to use a specific tool
type ToolCall struct {
	ID       string `json:"id"`
	Type     string `json:"type"`
	Function struct {
		Name      string `json:"name"`
		Arguments string `json:"arguments"`
	} `json:"function"`
}

// AlgoliaSearchParams represents the parameters for Algolia search
type AlgoliaSearchParams struct {
	Query string `json:"query"`
}

// StarterAppSearchParams represents the parameters for starter app search
type StarterAppSearchParams struct {
	Topics   []string `json:"topics"`
	Language string   `json:"language"`
}

// KapaQueryParams represents the parameters for Kapa queries
type KapaQueryParams struct {
	Question string   `json:"question"`
	Product  string   `json:"product"`
	Tags     []string `json:"tags"`
}

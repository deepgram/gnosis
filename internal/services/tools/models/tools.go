package models

import "encoding/json"

type ToolCall struct {
	ID       string `json:"id"`
	Type     string `json:"type"`
	Function struct {
		Name      string `json:"name"`
		Arguments string `json:"arguments"`
	} `json:"function"`
}

// Deepgram
type DeepgramToolCallConfig struct {
	Function struct {
		Name        string `json:"name"`
		Description string `json:"description"`
		URL         string `json:"url"`
		Headers     []struct {
			Key   string `json:"key"`
			Value string `json:"value"`
		} `json:"headers"`
		Method     string          `json:"method"`
		Parameters json.RawMessage `json:"parameters"`
	} `json:"function"`
}

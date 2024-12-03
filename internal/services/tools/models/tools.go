package models

import "encoding/json"

// Deepgram
type DeepgramToolCallConfig struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	Parameters  json.RawMessage `json:"parameters"`
}

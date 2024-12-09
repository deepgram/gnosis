package models

import "encoding/json"

// Deepgram
type DeepgramToolCallConfig struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	Parameters  json.RawMessage `json:"parameters"`
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

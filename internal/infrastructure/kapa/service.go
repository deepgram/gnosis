package kapa

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"sync"

	"github.com/deepgram/gnosis/internal/config"
)

type Service struct {
	mu        sync.RWMutex
	client    *http.Client
	projectID string
	baseURL   string
}

type QueryRequest struct {
	IntegrationID string    `json:"integration_id"`
	Query         string    `json:"query"`
	User          *UserInfo `json:"user,omitempty"`
}

type UserInfo struct {
	Email          string        `json:"email,omitempty"`
	UniqueClientID string        `json:"unique_client_id,omitempty"`
	FingerprintID  string        `json:"fingerprint_id,omitempty"`
	SlackID        string        `json:"slack_id,omitempty"`
	DiscordID      string        `json:"discord_id,omitempty"`
	Metadata       *UserMetadata `json:"metadata,omitempty"`
}

type UserMetadata struct {
	StoreIP bool `json:"store_ip"`
}

type QueryResponse struct {
	Answer           string           `json:"answer"`
	ThreadID         string           `json:"thread_id"`
	QuestionAnswerID string           `json:"question_answer_id"`
	IsUncertain      bool             `json:"is_uncertain"`
	RelevantSources  []RelevantSource `json:"relevant_sources"`
}

type RelevantSource struct {
	SourceURL            string `json:"source_url"`
	Title                string `json:"title"`
	ContainsInternalData bool   `json:"contains_internal_data"`
}

func NewService() *Service {
	projectID := config.GetKapaProjectID()
	apiKey := config.GetKapaAPIKey()
	integrationID := config.GetKapaIntegrationID()

	if projectID == "" || apiKey == "" || integrationID == "" {
		return nil
	}

	return &Service{
		mu:        sync.RWMutex{},
		client:    &http.Client{},
		projectID: projectID,
		baseURL:   "https://api.kapa.ai",
	}
}

func (s *Service) Query(ctx context.Context, question, product string, tags []string) (*QueryResponse, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	// Construct the request body
	req := QueryRequest{
		IntegrationID: config.GetKapaIntegrationID(),
		Query: fmt.Sprintf(`
			Question: %s
			Product: %v
			Tags: %v
		`, question, product, tags),
		User: &UserInfo{
			Metadata: &UserMetadata{
				StoreIP: false,
			},
		},
	}

	// Convert request to JSON
	jsonData, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}
	// Create the HTTP request
	url := fmt.Sprintf("%s/query/v1/projects/%s/chat/", s.baseURL, s.projectID)

	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set headers
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", config.GetKapaAPIKey()))
	httpReq.Header.Set("X-API-KEY", config.GetKapaAPIKey())

	// Make the request
	resp, err := s.client.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to make request: %w", err)
	}
	defer resp.Body.Close()

	// Check status code
	if resp.StatusCode != http.StatusOK {
		// Try to read error response body for debugging
		body, readErr := io.ReadAll(resp.Body)
		if readErr == nil {
			log.Printf("Error response body: %s", string(body))
		}
		return nil, fmt.Errorf("kapa API returned status %d", resp.StatusCode)
	}

	// Parse the response
	var queryResp QueryResponse
	if err := json.NewDecoder(resp.Body).Decode(&queryResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &queryResp, nil
}

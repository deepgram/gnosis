package kapa

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/deepgram/codename-sage/internal/config"
	"github.com/deepgram/codename-sage/internal/logger"
)

type Service struct {
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
	logger.Info("Initialising Kapa service")
	return &Service{
		client:    &http.Client{},
		projectID: config.GetKapaProjectID(),
		baseURL:   "https://api.kapa.ai",
	}
}

func (s *Service) Query(ctx context.Context, question, queryContext string, tags []string) (*QueryResponse, error) {
	logger.Info("Querying Kapa with question: %s", question)

	// Construct the request body
	req := QueryRequest{
		IntegrationID: config.GetKapaIntegrationID(),
		Query: fmt.Sprintf(`
			Question: %s
			Context: %s
			Tags: %v
		`, question, queryContext, tags),
		User: &UserInfo{
			Metadata: &UserMetadata{
				StoreIP: false,
			},
		},
	}

	// Convert request to JSON
	jsonData, err := json.Marshal(req)
	if err != nil {
		logger.Error("Failed to marshal request: %v", err)
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	// Create the HTTP request
	url := fmt.Sprintf("%s/query/v1/projects/%s/chat/", s.baseURL, s.projectID)
	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		logger.Error("Failed to create request: %v", err)
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set headers
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("X-API-KEY", config.GetKapaAPIKey())

	// Make the request
	resp, err := s.client.Do(httpReq)
	if err != nil {
		logger.Error("Failed to make request: %v", err)
		return nil, fmt.Errorf("failed to make request: %w", err)
	}
	defer resp.Body.Close()

	// Check status code
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		logger.Error("Kapa API returned non-200 status: %d\n\n%s", resp.StatusCode, string(body))
		return nil, fmt.Errorf("kapa API returned status %d: %s", resp.StatusCode, string(body))
	}

	// Parse the response
	var queryResp QueryResponse
	if err := json.NewDecoder(resp.Body).Decode(&queryResp); err != nil {
		logger.Error("Failed to decode response: %v", err)
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	logger.Debug("Successfully received response from Kapa")
	return &queryResp, nil
}

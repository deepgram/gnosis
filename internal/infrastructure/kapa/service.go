package kapa

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sync"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/pkg/logger"
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
	logger.Info(logger.SERVICE, "Initialising Kapa service")
	projectID := config.GetKapaProjectID()
	apiKey := config.GetKapaAPIKey()
	integrationID := config.GetKapaIntegrationID()

	if projectID == "" || apiKey == "" || integrationID == "" {
		logger.Warn(logger.SERVICE, "Kapa service not fully configured")
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

	logger.Info(logger.SERVICE, "Starting Kapa query")
	logger.Debug(logger.SERVICE, "Query parameters - question: %s, product: %s, tags: %v", question, product, tags)

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
	logger.Debug(logger.SERVICE, "Constructed query request with integration ID: %s", req.IntegrationID)

	// Convert request to JSON
	jsonData, err := json.Marshal(req)
	if err != nil {
		logger.Error(logger.SERVICE, "Failed to marshal request: %v", err)
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}
	logger.Debug(logger.SERVICE, "Request JSON: %s", string(jsonData))

	// Create the HTTP request
	url := fmt.Sprintf("%s/query/v1/projects/%s/chat/", s.baseURL, s.projectID)
	logger.Debug(logger.SERVICE, "Full request URL: %s", url)

	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		logger.Error(logger.SERVICE, "Failed to create request: %v", err)
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set headers
	logger.Debug(logger.SERVICE, "Setting request headers")
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", config.GetKapaAPIKey()))
	httpReq.Header.Set("X-API-KEY", config.GetKapaAPIKey())

	// Make the request
	logger.Debug(logger.SERVICE, "Sending HTTP request to Kapa API")
	resp, err := s.client.Do(httpReq)
	if err != nil {
		logger.Error(logger.SERVICE, "Failed to make request: %v", err)
		return nil, fmt.Errorf("failed to make request: %w", err)
	}
	defer resp.Body.Close()

	logger.Debug(logger.SERVICE, "Received response from Kapa API - Status: %d", resp.StatusCode)
	logger.Debug(logger.SERVICE, "Response headers:")
	for key, values := range resp.Header {
		logger.Debug(logger.SERVICE, "  %s: %v", key, values)
	}

	// Check status code
	if resp.StatusCode != http.StatusOK {
		logger.Error(logger.SERVICE, "Kapa API returned non-200 status: %d", resp.StatusCode)
		// Try to read error response body for debugging
		body, readErr := io.ReadAll(resp.Body)
		if readErr == nil {
			logger.Debug(logger.SERVICE, "Error response body: %s", string(body))
		}
		return nil, fmt.Errorf("kapa API returned status %d", resp.StatusCode)
	}

	// Parse the response
	var queryResp QueryResponse
	if err := json.NewDecoder(resp.Body).Decode(&queryResp); err != nil {
		logger.Error(logger.SERVICE, "Failed to decode response: %v", err)
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	logger.Debug(logger.SERVICE, "Successfully parsed response - Answer length: %d chars", len(queryResp.Answer))
	logger.Debug(logger.SERVICE, "Thread ID: %s, Question Answer ID: %s", queryResp.ThreadID, queryResp.QuestionAnswerID)
	logger.Debug(logger.SERVICE, "Is Uncertain: %v, Number of Relevant Sources: %d", queryResp.IsUncertain, len(queryResp.RelevantSources))

	for i, source := range queryResp.RelevantSources {
		logger.Debug(logger.SERVICE, "Source %d: Title=%s, URL=%s, Internal=%v",
			i+1, source.Title, source.SourceURL, source.ContainsInternalData)
	}

	return &queryResp, nil
}

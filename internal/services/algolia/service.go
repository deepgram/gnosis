package algolia

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
	appID     string
	apiKey    string
	indexName string
}

type SearchRequest struct {
	Query                string   `json:"query"`
	AttributesToRetrieve []string `json:"attributesToRetrieve"`
	HitsPerPage          int      `json:"hitsPerPage"`
	Filters              string   `json:"filters"`
}

type SearchResponse struct {
	Hits []struct {
		Title   string `json:"title"`
		Content string `json:"content"`
		URL     string `json:"url"`
	} `json:"hits"`
}

func NewService() *Service {
	logger.Info("Initialising Algolia service")
	return &Service{
		client:    &http.Client{},
		appID:     config.GetAlgoliaAppID(),
		apiKey:    config.GetAlgoliaAPIKey(),
		indexName: config.GetAlgoliaIndexName(),
	}
}

func (s *Service) Search(ctx context.Context, query string) (*SearchResponse, error) {
	logger.Info("Searching Algolia with query: %s", query)

	// Construct the request body
	req := SearchRequest{
		Query:                query,
		AttributesToRetrieve: []string{"title", "content", "url"},
		HitsPerPage:          1,
		Filters:              "type:content AND NOT content:null",
	}

	// Convert request to JSON
	jsonData, err := json.Marshal(req)
	if err != nil {
		logger.Error("Failed to marshal request: %v", err)
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	// Create the HTTP request
	url := fmt.Sprintf("https://%s-dsn.algolia.net/1/indexes/%s/query", s.appID, s.indexName)
	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		logger.Error("Failed to create request: %v", err)
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set headers
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("X-Algolia-API-Key", s.apiKey)
	httpReq.Header.Set("X-Algolia-Application-ID", s.appID)

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
		logger.Error("Algolia API returned non-200 status: %d\n\n%s", resp.StatusCode, string(body))
		return nil, fmt.Errorf("algolia API returned status %d: %s", resp.StatusCode, string(body))
	}

	// Parse the response
	var searchResp SearchResponse
	if err := json.NewDecoder(resp.Body).Decode(&searchResp); err != nil {
		logger.Error("Failed to decode response: %v", err)
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	logger.Debug("Successfully received response from Algolia")
	return &searchResp, nil
}

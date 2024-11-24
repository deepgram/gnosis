package algolia

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/logger"
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
	logger.Info(logger.SERVICE, "Initialising Algolia service")
	appID := config.GetAlgoliaAppID()
	apiKey := config.GetAlgoliaAPIKey()
	indexName := config.GetAlgoliaIndexName()

	if appID == "" || apiKey == "" || indexName == "" {
		logger.Warn(logger.SERVICE, "Algolia service not fully configured")
		return nil
	}

	return &Service{
		client:    &http.Client{},
		appID:     appID,
		apiKey:    apiKey,
		indexName: indexName,
	}
}

func (s *Service) Search(ctx context.Context, query string) (*SearchResponse, error) {
	logger.Info(logger.SERVICE, "Starting Algolia search")
	logger.Debug(logger.SERVICE, "Search parameters - query: %s", query)

	// Construct the request body
	req := SearchRequest{
		Query:                query,
		AttributesToRetrieve: []string{"title", "content", "url"},
		HitsPerPage:          1,
		Filters:              "type:content AND NOT content:null",
	}
	logger.Debug(logger.SERVICE, "Constructed search request with filters: %s", req.Filters)

	// Convert request to JSON
	jsonData, err := json.Marshal(req)
	if err != nil {
		logger.Error(logger.SERVICE, "Failed to marshal request: %v", err)
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}
	logger.Debug(logger.SERVICE, "Request JSON: %s", string(jsonData))

	// Create the HTTP request
	url := fmt.Sprintf("https://%s-dsn.algolia.net/1/indexes/%s/query", s.appID, s.indexName)
	logger.Debug(logger.SERVICE, "Full request URL: %s", url)

	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		logger.Error(logger.SERVICE, "Failed to create request: %v", err)
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set headers
	logger.Debug(logger.SERVICE, "Setting request headers")
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("X-Algolia-API-Key", s.apiKey)
	httpReq.Header.Set("X-Algolia-Application-ID", s.appID)

	// Make the request
	logger.Debug(logger.SERVICE, "Sending HTTP request to Algolia API")
	resp, err := s.client.Do(httpReq)
	if err != nil {
		logger.Error(logger.SERVICE, "Failed to make request: %v", err)
		return nil, fmt.Errorf("failed to make request: %w", err)
	}
	defer resp.Body.Close()

	logger.Debug(logger.SERVICE, "Received response from Algolia API - Status: %d", resp.StatusCode)
	logger.Debug(logger.SERVICE, "Response headers:")
	for key, values := range resp.Header {
		logger.Debug(logger.SERVICE, "  %s: %v", key, values)
	}

	// Check status code
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		logger.Error(logger.SERVICE, "Algolia API returned non-200 status: %d\n\n%s", resp.StatusCode, string(body))
		return nil, fmt.Errorf("algolia API returned status %d: %s", resp.StatusCode, string(body))
	}

	// Parse the response
	var searchResp SearchResponse
	if err := json.NewDecoder(resp.Body).Decode(&searchResp); err != nil {
		logger.Error(logger.SERVICE, "Failed to decode response: %v", err)
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	logger.Debug(logger.SERVICE, "Successfully parsed response - Found %d hits", len(searchResp.Hits))
	for i, hit := range searchResp.Hits {
		logger.Debug(logger.SERVICE, "Hit %d: Title=%s, URL=%s", i+1, hit.Title, hit.URL)
	}

	return &searchResp, nil
}

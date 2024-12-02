package algolia

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"sync"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/rs/zerolog/log"
)

type Service struct {
	mu        sync.RWMutex
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
	appID := config.GetAlgoliaAppID()
	apiKey := config.GetAlgoliaAPIKey()
	indexName := config.GetAlgoliaIndexName()

	if appID == "" || apiKey == "" || indexName == "" {
		log.Warn().Msg("Algolia API key not configured - function calls to Algolia will be unavailable")
		return nil
	}

	log.Info().
		Str("app_id", appID).
		Str("index", indexName).
		Msg("Algolia service initialized successfully")

	return &Service{
		mu:        sync.RWMutex{},
		client:    &http.Client{},
		appID:     appID,
		apiKey:    apiKey,
		indexName: indexName,
	}
}

func (s *Service) Search(ctx context.Context, query string) (*SearchResponse, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

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
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	// Create the HTTP request
	url := fmt.Sprintf("https://%s-dsn.algolia.net/1/indexes/%s/query", s.appID, s.indexName)

	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set headers
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("X-Algolia-API-Key", s.apiKey)
	httpReq.Header.Set("X-Algolia-Application-ID", s.appID)

	log.Info().
		Str("query", query).
		Int("hits_per_page", req.HitsPerPage).
		Str("filters", req.Filters).
		Msg("Executing Algolia search")

	// Make the request
	resp, err := s.client.Do(httpReq)
	if err != nil {
		log.Error().
			Err(err).
			Str("query", query).
			Str("index", s.indexName).
			Msg("Critical failure performing Algolia search")
		return nil, fmt.Errorf("algolia search failed: %w", err)
	}
	defer resp.Body.Close()

	// Check status code
	if resp.StatusCode != http.StatusOK {
		// Try to read error response body for debugging
		body, readErr := io.ReadAll(resp.Body)
		if readErr == nil {
			log.Printf("Error response body: %s", string(body))
		}

		return nil, fmt.Errorf("algolia API returned status %d", resp.StatusCode)
	}

	// Parse the response
	var searchResp SearchResponse
	if err := json.NewDecoder(resp.Body).Decode(&searchResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	log.Info().
		Int("hit_count", len(searchResp.Hits)).
		Str("query", query).
		Msg("Algolia search completed successfully")

	// Connection timeout or service unavailable
	if processingTime, err := strconv.Atoi(resp.Header.Get("X-Algolia-Processing-Time-MS")); err == nil && processingTime > 30000 {
		log.Error().
			Int("processingTime", processingTime).
			Str("query", query).
			Msg("Algolia search timeout - service may be degraded")
	}

	return &searchResp, nil
}

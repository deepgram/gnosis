package github

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sync"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/rs/zerolog/log"
)

type Service struct {
	mu      sync.RWMutex
	client  *http.Client
	token   string
	baseURL string
	headers map[string]string
}

type CodeSearchResponse struct {
	TotalCount int    `json:"total_count"`
	Items      []File `json:"items"`
}

type File struct {
	Name        string `json:"name"`
	Path        string `json:"path"`
	ContentsURL string `json:"contents_url"`
}

type ReposSearchResponse struct {
	TotalCount int          `json:"total_count"`
	Items      []Repository `json:"items"`
}

type ReadmeResponse struct {
	Type     string `json:"type"`
	Encoding string `json:"encoding"`
	Size     int    `json:"size"`
	Path     string `json:"path"`
	Content  string `json:"content"`
}

type Repository struct {
	Name        string `json:"name"`
	FullName    string `json:"full_name"`
	Description string `json:"description,omitempty"`
	Private     bool   `json:"private,omitempty"`
	HTMLURL     string `json:"html_url,omitempty"`
}

func NewService() *Service {
	token := config.GetGitHubToken()

	if token == "" {
		log.Warn().Msg("GitHub API token not configured - function calls to GitHubwill be unavailable")
		return nil
	}

	baseURL := "https://api.github.com"

	s := &Service{
		mu:      sync.RWMutex{},
		client:  &http.Client{},
		token:   token,
		baseURL: baseURL,
		headers: map[string]string{
			"Accept":               "application/vnd.github.v3+json",
			"X-GitHub-Api-Version": "2022-11-28",
			"Authorization":        fmt.Sprintf("Bearer %s", token),
		},
	}

	log.Info().
		Str("base_url", baseURL).
		Msg("GitHub service initialized successfully")

	return s
}

func (s *Service) SearchRepos(ctx context.Context, org, language string, topics []string) (*ReposSearchResponse, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	// Construct the search query
	query := fmt.Sprintf("org:%s", org)
	if language != "" {
		query += fmt.Sprintf("+language:%s", language)
	}
	for _, topic := range topics {
		query += fmt.Sprintf("+topic:%s", topic)
	}

	log.Info().
		Str("query", query).
		Msg("Executing GitHub repository search")

	url := fmt.Sprintf("%s/search/repositories?q=%s", s.baseURL, query)

	// Create request
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Make request
	resp, err := s.client.Do(req)
	if err != nil {
		log.Error().
			Err(err).
			Str("org", org).
			Str("language", language).
			Strs("topics", topics).
			Msg("Critical failure searching GitHub repositories")
		return nil, fmt.Errorf("github search failed: %w", err)
	}
	defer resp.Body.Close()

	// Check status code
	if resp.StatusCode != http.StatusOK {
		// Try to read error response body for debugging
		body, readErr := io.ReadAll(resp.Body)
		if readErr == nil {
			log.Printf("Error response body: %s", string(body))
		}

		return nil, fmt.Errorf("github API returned status %d", resp.StatusCode)
	}

	// Parse response
	var searchResp ReposSearchResponse
	if err := json.NewDecoder(resp.Body).Decode(&searchResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	log.Info().
		Int("total_count", searchResp.TotalCount).
		Int("repos_found", len(searchResp.Items)).
		Msg("GitHub repository search completed successfully")

	return &searchResp, nil
}

func (s *Service) GetRepoReadme(ctx context.Context, repo string) (*ReadmeResponse, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	url := fmt.Sprintf("%s/repos/%s/readme", s.baseURL, repo)

	// Create request
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Add headers
	for key, value := range s.headers {
		req.Header.Set(key, value)
	}

	// Make request
	resp, err := s.client.Do(req)
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

		return nil, fmt.Errorf("github API returned status %d", resp.StatusCode)
	}

	// Parse response
	var readme ReadmeResponse
	if err := json.NewDecoder(resp.Body).Decode(&readme); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &readme, nil
}

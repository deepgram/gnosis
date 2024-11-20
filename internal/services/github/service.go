package github

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/deepgram/codename-sage/internal/config"
	"github.com/deepgram/codename-sage/internal/logger"
)

type Service struct {
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
	logger.Info("Initialising GitHub service")
	token := config.GetGitHubToken()
	if token == "" {
		logger.Error("GitHub token is empty")
	} else {
		logger.Debug("GitHub token configured successfully")
	}
	return &Service{
		client:  &http.Client{},
		token:   config.GetGitHubToken(),
		baseURL: "https://api.github.com",
		headers: map[string]string{
			"Accept":               "application/vnd.github.v3+json",
			"X-GitHub-Api-Version": "2022-11-28",
			"Authorization":        fmt.Sprintf("Bearer %s", token),
		},
	}
}

func (s *Service) SearchRepos(ctx context.Context, org, language string, topics []string) (*ReposSearchResponse, error) {
	logger.Info("Starting GitHub repository search")
	logger.Debug("Search parameters - org: %s, language: %s, topics: %v", org, language, topics)

	// Construct the search query
	query := fmt.Sprintf("org:%s", org)
	if language != "" {
		query += fmt.Sprintf("+language:%s", language)
	}
	for _, topic := range topics {
		query += fmt.Sprintf("+topic:%s", topic)
	}
	logger.Debug("Constructed search query: %s", query)

	url := fmt.Sprintf("%s/search/repositories?q=%s", s.baseURL, query)
	logger.Debug("Full request URL: %s", url)

	// Create request
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		logger.Error("Failed to create request: %v", err)
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Log request headers for debugging
	logger.Debug("Setting request headers")
	for key, value := range s.headers {
		req.Header.Set(key, value)
		logger.Debug("Header set - %s: %s", key, value)
	}

	// Make request
	logger.Debug("Sending HTTP request to GitHub API")
	resp, err := s.client.Do(req)
	if err != nil {
		logger.Error("Failed to make request: %v", err)
		return nil, fmt.Errorf("failed to make request: %w", err)
	}
	defer resp.Body.Close()

	// Log response status and headers
	logger.Debug("Received response from GitHub API - Status: %d", resp.StatusCode)
	logger.Debug("Response headers:")
	for key, values := range resp.Header {
		logger.Debug("  %s: %v", key, values)
	}

	// Check status code
	if resp.StatusCode != http.StatusOK {
		logger.Error("GitHub API returned non-200 status: %d", resp.StatusCode)
		// Try to read error response body for debugging
		body, readErr := io.ReadAll(resp.Body)
		if readErr == nil {
			logger.Debug("Error response body: %s", string(body))
		}
		return nil, fmt.Errorf("github API returned status %d", resp.StatusCode)
	}

	// Parse response
	var searchResp ReposSearchResponse
	if err := json.NewDecoder(resp.Body).Decode(&searchResp); err != nil {
		logger.Error("Failed to decode response: %v", err)
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	logger.Debug("Successfully parsed response - Found %d repositories", searchResp.TotalCount)

	// Log repository details at debug level
	for i, repo := range searchResp.Items {
		logger.Debug("Repository %d: Name=%s, FullName=%s, Private=%v, URL=%s",
			i+1, repo.Name, repo.FullName, repo.Private, repo.HTMLURL)
	}

	return &searchResp, nil
}

func (s *Service) GetRepoReadme(ctx context.Context, repo string) (*ReadmeResponse, error) {
	logger.Info("Getting README for repo: %s", repo)

	url := fmt.Sprintf("%s/repos/%s/readme", s.baseURL, repo)
	logger.Debug("Requesting README from URL: %s", url)

	// Create request
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		logger.Error("Failed to create request: %v", err)
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Add headers logging
	logger.Debug("Setting request headers")
	for key, value := range s.headers {
		req.Header.Set(key, value)
		logger.Debug("Header set - %s: %s", key, value)
	}

	// Make request
	resp, err := s.client.Do(req)
	if err != nil {
		logger.Error("Failed to make request: %v", err)
		return nil, fmt.Errorf("failed to make request: %w", err)
	}
	defer resp.Body.Close()

	// Add response headers logging
	logger.Debug("Response headers:")
	for key, values := range resp.Header {
		logger.Debug("  %s: %v", key, values)
	}

	// Check status code
	if resp.StatusCode != http.StatusOK {
		logger.Error("GitHub API returned non-200 status: %d", resp.StatusCode)
		return nil, fmt.Errorf("github API returned status %d", resp.StatusCode)
	}

	// Parse response
	var readme ReadmeResponse
	if err := json.NewDecoder(resp.Body).Decode(&readme); err != nil {
		logger.Error("Failed to decode response: %v", err)
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	logger.Debug("Successfully received README for repo: %s", repo)
	return &readme, nil
}

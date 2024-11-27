package tools

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"

	"github.com/deepgram/gnosis/internal/domain/chat/models"
	"github.com/deepgram/gnosis/internal/infrastructure/algolia"
	"github.com/deepgram/gnosis/internal/infrastructure/github"
	"github.com/deepgram/gnosis/internal/infrastructure/kapa"
	"github.com/deepgram/gnosis/pkg/logger"
)

type ToolExecutor struct {
	algoliaService *algolia.Service
	githubService  *github.Service
	kapaService    *kapa.Service
}

func NewToolExecutor(
	algoliaService *algolia.Service,
	githubService *github.Service,
	kapaService *kapa.Service,
) *ToolExecutor {
	return &ToolExecutor{
		algoliaService: algoliaService,
		githubService:  githubService,
		kapaService:    kapaService,
	}
}

func (e *ToolExecutor) ExecuteToolCall(ctx context.Context, tool models.ToolCall) (string, error) {
	logger.Info(logger.TOOLS, "Executing tool call: %s", tool.Function.Name)
	if tool.Type != "function" {
		return "", fmt.Errorf("unsupported tool type")
	}

	switch tool.Function.Name {
	case "search_algolia":
		var params models.AlgoliaSearchParams
		if err := json.Unmarshal([]byte(tool.Function.Arguments), &params); err != nil {
			logger.Error(logger.TOOLS, "Failed to parse search parameters: %v", err)
			return "", fmt.Errorf("invalid parameters: %w", err)
		}

		result, err := e.algoliaService.Search(ctx, params.Query)
		if err != nil {
			return "", fmt.Errorf("algolia search failed: %w", err)
		}

		if len(result.Hits) == 0 {
			return "No relevant documentation found.", nil
		}

		hit := result.Hits[0]
		response := fmt.Sprintf("Found relevant documentation:\n\nTitle: %s\n\n%s\n\nSource: %s",
			hit.Title,
			hit.Content,
			hit.URL)

		logger.Debug(logger.TOOLS, "Algolia search response: %s", response)
		return response, nil

	case "search_starter_apps":
		var params models.StarterAppSearchParams
		if err := json.Unmarshal([]byte(tool.Function.Arguments), &params); err != nil {
			return "", fmt.Errorf("invalid parameters: %w", err)
		}

		searchResult, err := e.githubService.SearchRepos(ctx, "deepgram-starters", params.Language, params.Topics)
		if err != nil {
			return "", fmt.Errorf("github search failed: %w", err)
		}

		if len(searchResult.Items) == 0 {
			return "No relevant code samples found.", nil
		}

		repo := searchResult.Items[0]
		readmeResult, err := e.githubService.GetRepoReadme(ctx, repo.FullName)
		if err != nil {
			return "", fmt.Errorf("github readme failed: %w", err)
		}

		readmeContents, err := base64.StdEncoding.DecodeString(readmeResult.Content)
		if err != nil {
			return "", fmt.Errorf("unable to decode contents: %w", err)
		}

		response := fmt.Sprintf("Found relevant starter app:\n\nRepo: %s\nDescription: %s\nInstructions to use:\n%s",
			repo.HTMLURL,
			repo.Description,
			string(readmeContents),
		)

		logger.Info(logger.TOOLS, "Starter app search response: %s", response)
		return response, nil

	case "ask_kapa":
		var params models.KapaQueryParams
		if err := json.Unmarshal([]byte(tool.Function.Arguments), &params); err != nil {
			return "", fmt.Errorf("invalid parameters: %w", err)
		}

		resp, err := e.kapaService.Query(ctx, params.Question, params.Product, params.Tags)
		if err != nil {
			return "", fmt.Errorf("kapa query failed: %w", err)
		}

		return resp.Answer, nil

	default:
		return "", fmt.Errorf("unknown function: %s", tool.Function.Name)
	}
}

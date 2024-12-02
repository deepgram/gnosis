package tools

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"

	"github.com/deepgram/gnosis/internal/infrastructure/algolia"
	"github.com/deepgram/gnosis/internal/infrastructure/github"
	"github.com/deepgram/gnosis/internal/infrastructure/kapa"
	chatModels "github.com/deepgram/gnosis/internal/services/chat/models"
	toolsModels "github.com/deepgram/gnosis/internal/services/tools/models"
	"github.com/rs/zerolog/log"
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
	log.Info().
		Str("algolia", fmt.Sprintf("%v", algoliaService != nil)).
		Str("github", fmt.Sprintf("%v", githubService != nil)).
		Str("kapa", fmt.Sprintf("%v", kapaService != nil)).
		Msg("Initializing tool executor")

	log.Trace().
		Bool("has_algolia", algoliaService != nil).
		Bool("has_github", githubService != nil).
		Bool("has_kapa", kapaService != nil).
		Msg("Tool executor dependency details")

	log.Trace().
		Interface("algolia_config", algoliaService).
		Interface("github_config", githubService).
		Interface("kapa_config", kapaService).
		Msg("Initializing tool executor with service configurations")

	return &ToolExecutor{
		algoliaService: algoliaService,
		githubService:  githubService,
		kapaService:    kapaService,
	}
}

func (e *ToolExecutor) ExecuteToolCall(ctx context.Context, tool toolsModels.ToolCall) (string, error) {
	if tool.Type != "function" {
		log.Error().Str("type", tool.Type).Msg("Unsupported tool type requested")
		return "", fmt.Errorf("unsupported tool type")
	}

	log.Info().
		Str("tool_id", tool.ID).
		Str("tool_name", tool.Function.Name).
		Msg("Executing tool call")

	switch tool.Function.Name {
	case "search_algolia":
		if e.algoliaService == nil {
			log.Warn().
				Str("tool_id", tool.ID).
				Msg("Algolia search attempted but service not configured")
			return "", fmt.Errorf("algolia service not available")
		}

		var params chatModels.AlgoliaSearchParams
		if err := json.Unmarshal([]byte(tool.Function.Arguments), &params); err != nil {
			log.Error().Err(err).Str("tool", tool.Function.Name).Str("args", tool.Function.Arguments).Msg("Failed to parse Algolia search parameters")
			return "", fmt.Errorf("invalid parameters: %w", err)
		}

		result, err := e.algoliaService.Search(ctx, params.Query)
		if err != nil {
			log.Error().Err(err).Str("query", params.Query).Msg("Algolia search failed")
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

		log.Info().
			Str("tool_id", tool.ID).
			Str("tool_name", tool.Function.Name).
			Msg("Tool execution completed successfully")

		return response, nil

	case "search_starter_apps":
		if e.githubService == nil {
			log.Warn().
				Str("tool_id", tool.ID).
				Msg("GitHub search attempted but service not configured")
			return "", fmt.Errorf("github service not available")
		}

		var params chatModels.StarterAppSearchParams
		if err := json.Unmarshal([]byte(tool.Function.Arguments), &params); err != nil {
			log.Error().Err(err).Str("tool", tool.Function.Name).Str("args", tool.Function.Arguments).Msg("Failed to parse starter app search parameters")
			return "", fmt.Errorf("invalid parameters: %w", err)
		}

		searchResult, err := e.githubService.SearchRepos(ctx, "deepgram-starters", params.Language, params.Topics)
		if err != nil {
			log.Error().Err(err).
				Str("language", params.Language).
				Strs("topics", params.Topics).
				Msg("GitHub repository search failed")
			return "", fmt.Errorf("github search failed: %w", err)
		}

		if len(searchResult.Items) == 0 {
			return "No relevant code samples found.", nil
		}

		repo := searchResult.Items[0]
		readmeResult, err := e.githubService.GetRepoReadme(ctx, repo.FullName)
		if err != nil {
			log.Error().Err(err).
				Str("repo", repo.FullName).
				Msg("Failed to fetch repository README")
			return "", fmt.Errorf("github readme failed: %w", err)
		}

		readmeContents, err := base64.StdEncoding.DecodeString(readmeResult.Content)
		if err != nil {
			log.Error().Err(err).Str("tool", tool.Function.Name).Str("args", tool.Function.Arguments).Msg("Failed to decode README contents")
			return "", fmt.Errorf("unable to decode contents: %w", err)
		}

		response := fmt.Sprintf("Found relevant starter app:\n\nRepo: %s\nDescription: %s\nInstructions to use:\n%s",
			repo.HTMLURL,
			repo.Description,
			string(readmeContents),
		)

		log.Info().
			Str("tool_id", tool.ID).
			Str("tool_name", tool.Function.Name).
			Msg("Tool execution completed successfully")

		return response, nil

	case "ask_kapa":
		if e.kapaService == nil {
			log.Warn().
				Str("tool_id", tool.ID).
				Msg("Kapa query attempted but service not configured")
			return "", fmt.Errorf("kapa service not available")
		}

		var params chatModels.KapaQueryParams
		if err := json.Unmarshal([]byte(tool.Function.Arguments), &params); err != nil {
			log.Error().Err(err).Str("tool", tool.Function.Name).Str("args", tool.Function.Arguments).Msg("Failed to parse Kapa query parameters")
			return "", fmt.Errorf("invalid parameters: %w", err)
		}

		resp, err := e.kapaService.Query(ctx, params.Question, params.Product, params.Tags)
		if err != nil {
			log.Error().Err(err).Str("tool", tool.Function.Name).Str("args", tool.Function.Arguments).Msg("Kapa query failed")
			return "", fmt.Errorf("kapa query failed: %w", err)
		}

		log.Info().
			Str("tool_id", tool.ID).
			Str("tool_name", tool.Function.Name).
			Msg("Tool execution completed successfully")

		return resp.Answer, nil

	default:
		log.Warn().
			Str("tool_id", tool.ID).
			Str("function", tool.Function.Name).
			Msg("Client requested unknown tool function")
		return "", fmt.Errorf("unknown tool function")
	}
}

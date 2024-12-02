package openai

import (
	"context"
	"fmt"
	"strings"
	"sync"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/rs/zerolog/log"
	"github.com/sashabaranov/go-openai"
)

type Service struct {
	mu     sync.RWMutex
	client *openai.Client
}

func NewService() *Service {
	key := config.GetOpenAIKey()

	if key == "" {
		log.Fatal().Msg("OpenAI API key not configured - core chat functionality will be unavailable")
	}

	client := openai.NewClient(key)
	if client == nil {
		log.Fatal().Msg("Failed to initialize OpenAI client")
	}

	return &Service{
		mu:     sync.RWMutex{},
		client: client,
	}
}

func (s *Service) GetClient() *openai.Client {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.client
}

func (s *Service) CreateChatCompletion(ctx context.Context, req *openai.ChatCompletionRequest) (*openai.ChatCompletionResponse, error) {
	resp, err := s.client.CreateChatCompletion(ctx, *req)
	if err != nil {
		if strings.Contains(err.Error(), "connection refused") ||
			strings.Contains(err.Error(), "timeout") ||
			strings.Contains(err.Error(), "rate limit") {
			log.Error().
				Err(err).
				Interface("request", req).
				Msg("Critical failure communicating with OpenAI API")
			return nil, fmt.Errorf("openai service unavailable: %w", err)
		}
		return nil, err
	}

	if resp.Usage.TotalTokens > 7000 {
		log.Error().
			Int("tokens", resp.Usage.TotalTokens).
			Msg("Excessive token usage detected in OpenAI request")
	}

	return &resp, nil
}

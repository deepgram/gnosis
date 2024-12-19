package openai

import (
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

	log.Info().Msg("OpenAI client initialized successfully")

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

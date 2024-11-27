package openai

import (
	"sync"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/pkg/logger"
	"github.com/sashabaranov/go-openai"
)

type Service struct {
	mu     sync.RWMutex
	client *openai.Client
}

func NewService() *Service {
	logger.Info(logger.SERVICE, "Initialising OpenAI service")
	key := config.GetOpenAIKey()

	if key == "" {
		logger.Warn(logger.SERVICE, "OpenAI service not configured - OPENAI_KEY missing")
		return nil
	}

	return &Service{
		mu:     sync.RWMutex{},
		client: openai.NewClient(key),
	}
}

func (s *Service) GetClient() *openai.Client {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.client
}

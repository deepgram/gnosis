package openai

import (
	"log"
	"sync"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/sashabaranov/go-openai"
)

type Service struct {
	mu     sync.RWMutex
	client *openai.Client
}

func NewService() *Service {
	key := config.GetOpenAIKey()

	if key == "" {
		log.Fatal("OpenAI service not configured - OPENAI_KEY missing")
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

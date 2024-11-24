package services

import (
	"fmt"
	"sync"

	"github.com/deepgram/gnosis/internal/logger"
	"github.com/deepgram/gnosis/internal/services/algolia"
	"github.com/deepgram/gnosis/internal/services/chat"
	"github.com/deepgram/gnosis/internal/services/github"
	"github.com/deepgram/gnosis/internal/services/kapa"
	"github.com/deepgram/gnosis/internal/services/redis"
	"github.com/deepgram/gnosis/internal/services/session"
	"github.com/deepgram/gnosis/internal/services/tools"
)

var (
	// Mutex for thread-safe initialization
	servicesMu sync.RWMutex
)

type Services struct {
	algoliaService *algolia.Service
	githubService  *github.Service
	kapaService    *kapa.Service
	redisService   *redis.Service
	sessionService *session.Service
	chatService    *chat.Service
	toolsService   *tools.Service
}

// InitializeServices initializes all required services
func InitializeServices() (*Services, error) {
	servicesMu.Lock()
	defer servicesMu.Unlock()

	logger.Info(logger.SERVICE, "Initializing services")

	// Initialize optional services
	algoliaService := algolia.NewService()
	githubService := github.NewService()
	kapaService := kapa.NewService()
	redisService := redis.NewService()

	// Initialize session service with Redis dependency
	sessionService := session.NewService(redisService)

	// Initialize tools service with dependencies
	toolsService, err := tools.NewService(algoliaService, githubService, kapaService)
	if err != nil {
		logger.Error(logger.SERVICE, "Failed to initialize tools service: %v", err)
		return nil, fmt.Errorf("failed to initialize tools service: %w", err)
	}

	// Initialize chat service with dependencies
	chatService := chat.NewService(algoliaService, githubService, kapaService, toolsService)

	logger.Info(logger.SERVICE, "Services initialization complete")

	return &Services{
		algoliaService: algoliaService,
		githubService:  githubService,
		kapaService:    kapaService,
		redisService:   redisService,
		sessionService: sessionService,
		chatService:    chatService,
		toolsService:   toolsService,
	}, nil
}

// Add a getter method for the chat service
func (s *Services) GetChatService() *chat.Service {
	return s.chatService
}

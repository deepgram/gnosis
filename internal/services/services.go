package services

import (
	"fmt"
	"os"
	"sync"

	"github.com/deepgram/gnosis/internal/infrastructure/algolia"
	"github.com/deepgram/gnosis/internal/infrastructure/github"
	"github.com/deepgram/gnosis/internal/infrastructure/kapa"
	"github.com/deepgram/gnosis/internal/infrastructure/openai"
	"github.com/deepgram/gnosis/internal/infrastructure/redis"
	"github.com/deepgram/gnosis/internal/services/authcode"
	chatimpl "github.com/deepgram/gnosis/internal/services/chat"
	"github.com/deepgram/gnosis/internal/services/session"
	"github.com/deepgram/gnosis/internal/services/tools"
	"github.com/deepgram/gnosis/pkg/logger"
)

var (
	// Mutex for thread-safe initialization
	servicesMu sync.RWMutex
)

type Services struct {
	algoliaService  *algolia.Service
	githubService   *github.Service
	kapaService     *kapa.Service
	redisService    *redis.Service
	sessionService  *session.Service
	chatService     *chatimpl.Implementation
	openAIService   *openai.Service
	toolExecutor    *tools.ToolExecutor
	authCodeService *authcode.Service
}

// InitializeServices initializes all required services
func InitializeServices() (*Services, error) {
	servicesMu.Lock()
	defer servicesMu.Unlock()

	logger.Info(logger.SERVICE, "Initializing services")

	// Initialize OpenAI service
	openAIService := openai.NewService()
	if openAIService == nil {
		logger.Fatal(logger.SERVICE, "Failed to initialize OpenAI service")
		os.Exit(1)
	}

	// Initialize infrastructure services
	algoliaService := algolia.NewService()
	if algoliaService == nil {
		logger.Warn(logger.SERVICE, "Failed to initialize Algolia service")
		return nil, fmt.Errorf("failed to initialize Algolia service")
	}

	githubService := github.NewService()
	if githubService == nil {
		logger.Warn(logger.SERVICE, "Failed to initialize GitHub service")
		return nil, fmt.Errorf("failed to initialize GitHub service")
	}

	kapaService := kapa.NewService()
	if kapaService == nil {
		logger.Warn(logger.SERVICE, "Failed to initialize Kapa service")
		return nil, fmt.Errorf("failed to initialize Kapa service")
	}

	// Initialize Redis service
	redisService := redis.NewService()
	if redisService == nil {
		logger.Warn(logger.SERVICE, "Failed to initialize Redis service")
		return nil, fmt.Errorf("failed to initialize Redis service")
	}

	// Initialize tool executor
	toolExecutor := tools.NewToolExecutor(algoliaService, githubService, kapaService)

	// Initialize session service
	sessionService := session.NewService(redisService)

	// Initialize auth code service
	authCodeService := authcode.NewService(redisService)

	// Initialize chat service
	chatService, err := chatimpl.NewService(openAIService, toolExecutor)
	if err != nil {
		logger.Error(logger.SERVICE, "Failed to initialize chat service: %v", err)
		return nil, fmt.Errorf("failed to initialize chat service: %w", err)
	}

	logger.Info(logger.SERVICE, "Services initialization complete")

	return &Services{
		algoliaService:  algoliaService,
		githubService:   githubService,
		kapaService:     kapaService,
		redisService:    redisService,
		sessionService:  sessionService,
		chatService:     chatService,
		openAIService:   openAIService,
		toolExecutor:    toolExecutor,
		authCodeService: authCodeService,
	}, nil
}

// GetChatService returns the chat service
func (s *Services) GetChatService() *chatimpl.Implementation {
	return s.chatService
}

// GetAuthCodeService returns the auth code service
func (s *Services) GetAuthCodeService() *authcode.Service {
	return s.authCodeService
}

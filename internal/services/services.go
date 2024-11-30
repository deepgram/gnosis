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
	"github.com/deepgram/gnosis/internal/services/chat"
	"github.com/deepgram/gnosis/internal/services/session"
	"github.com/deepgram/gnosis/internal/services/tools"
	"github.com/deepgram/gnosis/internal/services/widgetcode"
	"github.com/deepgram/gnosis/pkg/logger"
)

var (
	// Mutex for thread-safe initialization
	servicesMu sync.RWMutex
)

type Services struct {
	algoliaService    *algolia.Service
	githubService     *github.Service
	kapaService       *kapa.Service
	redisService      *redis.Service
	sessionService    *session.Service
	chatService       *chat.Implementation
	openAIService     *openai.Service
	toolExecutor      *tools.ToolExecutor
	widgetCodeService *widgetcode.Service
}

// InitializeServices initializes all required services
func InitializeServices() (*Services, error) {
	servicesMu.Lock()
	defer servicesMu.Unlock()

	logger.Info(logger.SERVICE, "Initializing services")

	// Initialize OpenAI service (required)
	openAIService := openai.NewService()
	if openAIService == nil {
		logger.Fatal(logger.SERVICE, "Failed to initialize OpenAI service")
		os.Exit(1)
	}

	// Initialize Redis service (optional)
	redisService := redis.NewService()
	if redisService == nil {
		logger.Info(logger.SERVICE, "Redis service not configured - using in-memory storage")
	}

	// Initialize optional infrastructure services
	algoliaService := algolia.NewService()
	if algoliaService == nil {
		logger.Info(logger.SERVICE, "Algolia service not configured - functionality will be limited")
	}

	githubService := github.NewService()
	if githubService == nil {
		logger.Info(logger.SERVICE, "GitHub service not configured - functionality will be limited")
	}

	kapaService := kapa.NewService()
	if kapaService == nil {
		logger.Info(logger.SERVICE, "Kapa service not configured - functionality will be limited")
	}

	// Initialize tool executor with optional services
	toolExecutor := tools.NewToolExecutor(algoliaService, githubService, kapaService)

	// Initialize session service with optional Redis
	sessionService := session.NewService(redisService)

	// Initialize widget code service with optional Redis
	widgetCodeService := widgetcode.NewService(redisService)

	// Initialize chat service (required)
	chatService, err := chat.NewService(openAIService, toolExecutor)
	if err != nil {
		logger.Error(logger.SERVICE, "Failed to initialize chat service: %v", err)
		return nil, fmt.Errorf("failed to initialize chat service: %w", err)
	}

	logger.Info(logger.SERVICE, "Services initialization complete")

	return &Services{
		algoliaService:    algoliaService,
		githubService:     githubService,
		kapaService:       kapaService,
		redisService:      redisService,
		sessionService:    sessionService,
		chatService:       chatService,
		openAIService:     openAIService,
		toolExecutor:      toolExecutor,
		widgetCodeService: widgetCodeService,
	}, nil
}

// GetChatService returns the chat service
func (s *Services) GetChatService() *chat.Implementation {
	return s.chatService
}

// GetWidgetCodeService returns the widget code service
func (s *Services) GetWidgetCodeService() *widgetcode.Service {
	return s.widgetCodeService
}

// GetSessionService returns the session service
func (s *Services) GetSessionService() *session.Service {
	return s.sessionService
}

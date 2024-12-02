package services

import (
	"fmt"
	"log"
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

	// Initialize OpenAI service (required)
	openAIService := openai.NewService()
	if openAIService == nil {
		log.Fatal("Failed to initialize OpenAI service")
	}

	// Initialize Redis service (optional)
	redisService := redis.NewService()

	// Initialize optional infrastructure services
	algoliaService := algolia.NewService()
	githubService := github.NewService()
	kapaService := kapa.NewService()

	// Initialize tool executor with optional services
	toolExecutor := tools.NewToolExecutor(algoliaService, githubService, kapaService)

	// Initialize session service with optional Redis
	sessionService := session.NewService(redisService)

	// Initialize widget code service with optional Redis
	widgetCodeService := widgetcode.NewService(redisService)

	// Initialize chat service (required)
	chatService, err := chat.NewService(openAIService, toolExecutor)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize chat service: %w", err)
	}

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

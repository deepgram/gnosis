package services

import (
	"fmt"
	"sync"

	"github.com/deepgram/gnosis/internal/infrastructure/algolia"
	"github.com/deepgram/gnosis/internal/infrastructure/deepgram"
	"github.com/deepgram/gnosis/internal/infrastructure/github"
	"github.com/deepgram/gnosis/internal/infrastructure/kapa"
	"github.com/deepgram/gnosis/internal/infrastructure/openai"
	"github.com/deepgram/gnosis/internal/infrastructure/redis"
	"github.com/deepgram/gnosis/internal/services/chat"
	"github.com/deepgram/gnosis/internal/services/proxy"
	"github.com/deepgram/gnosis/internal/services/session"
	"github.com/deepgram/gnosis/internal/services/tools"
	"github.com/deepgram/gnosis/internal/services/widgetcode"
	"github.com/rs/zerolog/log"
)

var (
	// Mutex for thread-safe initialization
	servicesMu sync.RWMutex
)

type Services struct {
	algoliaService    *algolia.Service
	chatService       *chat.Implementation
	deepgramService   *deepgram.Service
	githubService     *github.Service
	kapaService       *kapa.Service
	openAIService     *openai.Service
	agentProxyService *proxy.Service
	redisService      *redis.Service
	sessionService    *session.Service
	toolService       *tools.Service
	widgetCodeService *widgetcode.Service
}

// InitializeServices initializes all required services
func InitializeServices() (*Services, error) {
	servicesMu.Lock()
	defer servicesMu.Unlock()

	log.Info().Msg("Initializing core services")

	// Initialize Redis service (optional)
	redisService := redis.NewService()
	log.Info().Msg("Initializing Redis service")

	// Initialize optional infrastructure services
	algoliaService := algolia.NewService()
	githubService := github.NewService()
	kapaService := kapa.NewService()
	log.Info().Msg("Initializing infrastructure services")

	toolService := tools.NewService(algoliaService, githubService, kapaService)
	log.Info().Msg("Initializing tool service")

	// Initialize session service with optional Redis
	sessionService := session.NewService(redisService)
	log.Info().Msg("Initializing session service")

	// Initialize widget code service with optional Redis
	widgetCodeService := widgetcode.NewService(redisService)
	log.Info().Msg("Initializing widget code service")

	// Initialize Deepgram service (required)
	deepgramService := deepgram.NewService()
	if deepgramService == nil {
		log.Fatal().Msg("Failed to initialize Deepgram service - service is required for core functionality")
	}

	// Initialize Deepgram service (required)
	agentProxyService := proxy.NewAgentService(deepgramService)
	if agentProxyService == nil {
		log.Fatal().Msg("Failed to initialize Proxy service - service is required for core functionality")
	}

	// Initialize OpenAI service (required)
	openAIService := openai.NewService()
	if openAIService == nil {
		log.Fatal().Msg("Failed to initialize OpenAI service - service is required for core functionality")
	}

	// Initialize chat service (required)
	chatService, err := chat.NewService(openAIService, toolService)
	if err != nil {
		log.Error().Err(err).Msg("Failed to initialize chat service - required for message processing")
		return nil, fmt.Errorf("failed to initialize chat service: %w", err)
	}
	log.Info().Msg("Initializing chat service")

	log.Info().Msg("All services initialized successfully")

	return &Services{
		algoliaService:    algoliaService,
		chatService:       chatService,
		deepgramService:   deepgramService,
		githubService:     githubService,
		kapaService:       kapaService,
		openAIService:     openAIService,
		agentProxyService: agentProxyService,
		redisService:      redisService,
		sessionService:    sessionService,
		toolService:       toolService,
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

// GetToolService returns the tool service
func (s *Services) GetToolService() *tools.Service {
	return s.toolService
}

// GetAgentProxyService returns the agent proxy service
func (s *Services) GetAgentProxyService() *proxy.Service {
	return s.agentProxyService
}

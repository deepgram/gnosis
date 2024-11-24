package services

import (
	"sync"

	"github.com/deepgram/gnosis/internal/logger"
	"github.com/deepgram/gnosis/internal/services/algolia"
	"github.com/deepgram/gnosis/internal/services/github"
	"github.com/deepgram/gnosis/internal/services/kapa"
	"github.com/deepgram/gnosis/internal/services/redis"
	"github.com/deepgram/gnosis/internal/services/session"
)

var (
	// Service instances
	algoliaService *algolia.Service
	githubService  *github.Service
	kapaService    *kapa.Service
	redisService   *redis.Service
	sessionService *session.Service

	// Mutex for thread-safe initialization
	servicesMu  sync.RWMutex
	initialized bool
)

// InitializeServices initializes all required services
func InitializeServices() error {
	servicesMu.Lock()
	defer servicesMu.Unlock()

	if initialized {
		logger.Debug(logger.SERVICE, "Services already initialized")
		return nil
	}

	logger.Info(logger.SERVICE, "Initializing services")

	// Initialize optional services
	algoliaService = algolia.NewService()
	githubService = github.NewService()
	kapaService = kapa.NewService()
	redisService = redis.NewService()

	// Initialize session service with Redis dependency
	sessionService = session.NewService(redisService)

	initialized = true
	logger.Info(logger.SERVICE, "Services initialization complete")
	return nil
}

// Getter methods for each service
func GetAlgoliaService() *algolia.Service {
	servicesMu.RLock()
	defer servicesMu.RUnlock()
	return algoliaService
}

func GetGitHubService() *github.Service {
	servicesMu.RLock()
	defer servicesMu.RUnlock()
	return githubService
}

func GetKapaService() *kapa.Service {
	servicesMu.RLock()
	defer servicesMu.RUnlock()
	return kapaService
}

func GetRedisService() *redis.Service {
	servicesMu.RLock()
	defer servicesMu.RUnlock()
	return redisService
}

func GetSessionService() *session.Service {
	servicesMu.RLock()
	defer servicesMu.RUnlock()
	return sessionService
}

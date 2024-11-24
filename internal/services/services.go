package services

import (
	"sync"

	"github.com/deepgram/gnosis/internal/logger"
	"github.com/deepgram/gnosis/internal/services/session"
)

var (
	SessionService *session.Service
	servicesMu     sync.RWMutex
	initialized    bool
)

// InitializeServices initializes all required services
func InitializeServices() error {
	servicesMu.Lock()
	defer servicesMu.Unlock()

	if initialized {
		logger.Debug("Services already initialized")
		return nil
	}

	logger.Info("Initializing services")

	// Initialize session service
	SessionService = session.NewService()

	initialized = true
	return nil
}

// GetSessionService returns the session service in a thread-safe manner
func GetSessionService() *session.Service {
	servicesMu.RLock()
	defer servicesMu.RUnlock()
	return SessionService
}

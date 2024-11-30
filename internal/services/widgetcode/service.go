package widgetcode

import (
	"context"
	"encoding/json"
	"sync"
	"time"

	"github.com/deepgram/gnosis/internal/infrastructure/redis"
	"github.com/deepgram/gnosis/pkg/logger"
)

const (
	WidgetCodeLifetime = 10 * time.Minute
)

type WidgetCodeInfo struct {
	ClientID  string    `json:"client_id"`
	State     string    `json:"state"`
	ExpiresAt time.Time `json:"expires_at"`
}

type WidgetCodeStore interface {
	Set(ctx context.Context, code string, info *WidgetCodeInfo) error
	Get(ctx context.Context, code string) (*WidgetCodeInfo, error)
	Delete(ctx context.Context, code string) error
}

type RedisStore struct {
	redisService *redis.Service
}

type MemoryStore struct {
	mu          sync.RWMutex
	WidgetCodes map[string]*WidgetCodeInfo
}

type Service struct {
	store WidgetCodeStore
}

func NewService(redisService *redis.Service) *Service {
	logger.Info(logger.SERVICE, "Initialising widget code service")

	var store WidgetCodeStore
	if redisService != nil {
		logger.Info(logger.SERVICE, "Using Redis for widget code storage")

		// Test Redis connection
		ctx := context.Background()
		if err := redisService.Ping(ctx); err != nil {
			logger.Error(logger.SERVICE, "Redis connection failed: %v", err)
			logger.Warn(logger.SERVICE, "Falling back to in-memory widget code storage")
			store = newMemoryStore()
		} else {
			store = &RedisStore{redisService: redisService}
		}
	} else {
		logger.Info(logger.SERVICE, "Using in-memory widget code storage")
		store = newMemoryStore()
	}

	return &Service{store: store}
}

func newMemoryStore() *MemoryStore {
	return &MemoryStore{
		WidgetCodes: make(map[string]*WidgetCodeInfo),
	}
}

// Redis Store implementation
func (rs *RedisStore) Set(ctx context.Context, code string, info *WidgetCodeInfo) error {
	data, err := json.Marshal(info)
	if err != nil {
		return err
	}

	return rs.redisService.Set(ctx, "WidgetCode:"+code, string(data), WidgetCodeLifetime)
}

func (rs *RedisStore) Get(ctx context.Context, code string) (*WidgetCodeInfo, error) {
	data, err := rs.redisService.Get(ctx, "WidgetCode:"+code)
	if err != nil {
		return nil, err
	}

	var info WidgetCodeInfo
	if err := json.Unmarshal([]byte(data), &info); err != nil {
		return nil, err
	}

	// Check expiration
	if time.Now().After(info.ExpiresAt) {
		if err := rs.Delete(ctx, code); err != nil {
			logger.Warn(logger.SERVICE, "Failed to delete widget code: %v", err)
		}
		return nil, nil
	}

	return &info, nil
}

func (rs *RedisStore) Delete(ctx context.Context, code string) error {
	return rs.redisService.Delete(ctx, "WidgetCode:"+code)
}

// Memory Store implementation
func (ms *MemoryStore) Set(ctx context.Context, code string, info *WidgetCodeInfo) error {
	ms.mu.Lock()
	defer ms.mu.Unlock()
	ms.WidgetCodes[code] = info
	return nil
}

func (ms *MemoryStore) Get(ctx context.Context, code string) (*WidgetCodeInfo, error) {
	ms.mu.RLock()
	defer ms.mu.RUnlock()

	info, exists := ms.WidgetCodes[code]
	if !exists {
		return nil, nil
	}

	// Check expiration
	if time.Now().After(info.ExpiresAt) {
		if err := ms.Delete(ctx, code); err != nil {
			logger.Warn(logger.SERVICE, "Failed to delete widget code: %v", err)
		}
		return nil, nil
	}

	return info, nil
}

func (ms *MemoryStore) Delete(ctx context.Context, code string) error {
	ms.mu.Lock()
	defer ms.mu.Unlock()
	delete(ms.WidgetCodes, code)
	return nil
}

// Service methods
func (s *Service) StoreWidgetCode(ctx context.Context, code, clientID, state string) error {
	info := &WidgetCodeInfo{
		ClientID:  clientID,
		State:     state,
		ExpiresAt: time.Now().Add(WidgetCodeLifetime),
	}
	return s.store.Set(ctx, code, info)
}

func (s *Service) ValidateWidgetCode(ctx context.Context, code string) (*WidgetCodeInfo, error) {
	return s.store.Get(ctx, code)
}

func (s *Service) InvalidateWidgetCode(ctx context.Context, code string) error {
	return s.store.Delete(ctx, code)
}

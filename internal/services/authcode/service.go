package authcode

import (
	"context"
	"encoding/json"
	"sync"
	"time"

	"github.com/deepgram/gnosis/internal/services/redis"
	"github.com/deepgram/gnosis/pkg/logger"
)

const (
	authCodeLifetime = 10 * time.Minute
)

type AuthCodeInfo struct {
	ClientID  string    `json:"client_id"`
	State     string    `json:"state"`
	ExpiresAt time.Time `json:"expires_at"`
}

type AuthCodeStore interface {
	Set(ctx context.Context, code string, info *AuthCodeInfo) error
	Get(ctx context.Context, code string) (*AuthCodeInfo, error)
	Delete(ctx context.Context, code string) error
}

type RedisStore struct {
	redisService *redis.Service
}

type MemoryStore struct {
	mu        sync.RWMutex
	authCodes map[string]*AuthCodeInfo
}

type Service struct {
	store AuthCodeStore
}

func NewService(redisService *redis.Service) *Service {
	logger.Info(logger.SERVICE, "Initialising auth code service")

	var store AuthCodeStore
	if redisService != nil {
		logger.Info(logger.SERVICE, "Using Redis for auth code storage")

		// Test Redis connection
		ctx := context.Background()
		if err := redisService.Ping(ctx); err != nil {
			logger.Error(logger.SERVICE, "Redis connection failed: %v", err)
			logger.Warn(logger.SERVICE, "Falling back to in-memory auth code storage")
			store = newMemoryStore()
		} else {
			store = &RedisStore{redisService: redisService}
		}
	} else {
		logger.Info(logger.SERVICE, "Using in-memory auth code storage")
		store = newMemoryStore()
	}

	return &Service{store: store}
}

func newMemoryStore() *MemoryStore {
	return &MemoryStore{
		authCodes: make(map[string]*AuthCodeInfo),
	}
}

// Redis Store implementation
func (rs *RedisStore) Set(ctx context.Context, code string, info *AuthCodeInfo) error {
	data, err := json.Marshal(info)
	if err != nil {
		return err
	}

	return rs.redisService.Set(ctx, "authcode:"+code, string(data), authCodeLifetime)
}

func (rs *RedisStore) Get(ctx context.Context, code string) (*AuthCodeInfo, error) {
	data, err := rs.redisService.Get(ctx, "authcode:"+code)
	if err != nil {
		return nil, err
	}

	var info AuthCodeInfo
	if err := json.Unmarshal([]byte(data), &info); err != nil {
		return nil, err
	}

	// Check expiration
	if time.Now().After(info.ExpiresAt) {
		if err := rs.Delete(ctx, code); err != nil {
			logger.Warn(logger.SERVICE, "Failed to delete auth code: %v", err)
		}
		return nil, nil
	}

	return &info, nil
}

func (rs *RedisStore) Delete(ctx context.Context, code string) error {
	return rs.redisService.Delete(ctx, "authcode:"+code)
}

// Memory Store implementation
func (ms *MemoryStore) Set(ctx context.Context, code string, info *AuthCodeInfo) error {
	ms.mu.Lock()
	defer ms.mu.Unlock()
	ms.authCodes[code] = info
	return nil
}

func (ms *MemoryStore) Get(ctx context.Context, code string) (*AuthCodeInfo, error) {
	ms.mu.RLock()
	defer ms.mu.RUnlock()

	info, exists := ms.authCodes[code]
	if !exists {
		return nil, nil
	}

	// Check expiration
	if time.Now().After(info.ExpiresAt) {
		if err := ms.Delete(ctx, code); err != nil {
			logger.Warn(logger.SERVICE, "Failed to delete auth code: %v", err)
		}
		return nil, nil
	}

	return info, nil
}

func (ms *MemoryStore) Delete(ctx context.Context, code string) error {
	ms.mu.Lock()
	defer ms.mu.Unlock()
	delete(ms.authCodes, code)
	return nil
}

// Service methods
func (s *Service) StoreAuthCode(ctx context.Context, code, clientID, state string) error {
	info := &AuthCodeInfo{
		ClientID:  clientID,
		State:     state,
		ExpiresAt: time.Now().Add(authCodeLifetime),
	}
	return s.store.Set(ctx, code, info)
}

func (s *Service) ValidateAuthCode(ctx context.Context, code string) (*AuthCodeInfo, error) {
	return s.store.Get(ctx, code)
}

func (s *Service) InvalidateAuthCode(ctx context.Context, code string) error {
	return s.store.Delete(ctx, code)
}

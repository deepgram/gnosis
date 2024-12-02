package redis

import (
	"context"
	"sync"
	"time"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/redis/go-redis/v9"
)

type Service struct {
	client *redis.Client
}

var (
	redisService *Service
	redisMu      sync.RWMutex
)

func GetService() *Service {
	redisMu.RLock()
	defer redisMu.RUnlock()
	return redisService
}

func NewService() *Service {
	url := config.GetRedisURL()

	if url == "" {
		return nil
	}

	client := redis.NewClient(&redis.Options{
		Addr:     url,
		Password: config.GetRedisPassword(),
		DB:       0,
	})

	return &Service{
		client: client,
	}
}

// Set stores a value in Redis with an optional expiration
func (s *Service) Set(ctx context.Context, key string, value interface{}, expiration time.Duration) error {
	return s.client.Set(ctx, key, value, expiration).Err()
}

// Get retrieves a value from Redis
func (s *Service) Get(ctx context.Context, key string) (string, error) {
	return s.client.Get(ctx, key).Result()
}

// Delete removes a key from Redis
func (s *Service) Delete(ctx context.Context, key string) error {
	return s.client.Del(ctx, key).Err()
}

// Ping checks if Redis is accessible
func (s *Service) Ping(ctx context.Context) error {
	return s.client.Ping(ctx).Err()
}

// Close closes the Redis connection
func (s *Service) Close() error {
	return s.client.Close()
}

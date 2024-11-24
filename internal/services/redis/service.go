package redis

import (
	"context"
	"sync"
	"time"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/logger"
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
	logger.Info(logger.SERVICE, "Initialising Redis service")
	url := config.GetRedisURL()

	if url == "" {
		logger.Warn(logger.SERVICE, "Redis service not configured - REDIS_URL missing")
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
	logger.Debug(logger.SERVICE, "Setting Redis key: %s", key)
	return s.client.Set(ctx, key, value, expiration).Err()
}

// Get retrieves a value from Redis
func (s *Service) Get(ctx context.Context, key string) (string, error) {
	logger.Debug(logger.SERVICE, "Getting Redis key: %s", key)
	return s.client.Get(ctx, key).Result()
}

// Delete removes a key from Redis
func (s *Service) Delete(ctx context.Context, key string) error {
	logger.Debug(logger.SERVICE, "Deleting Redis key: %s", key)
	return s.client.Del(ctx, key).Err()
}

// Ping checks if Redis is accessible
func (s *Service) Ping(ctx context.Context) error {
	logger.Debug(logger.SERVICE, "Pinging Redis server")
	return s.client.Ping(ctx).Err()
}

// Close closes the Redis connection
func (s *Service) Close() error {
	logger.Debug(logger.SERVICE, "Closing Redis connection")
	return s.client.Close()
}

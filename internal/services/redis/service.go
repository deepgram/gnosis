package redis

import (
	"context"
	"time"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/logger"
	"github.com/redis/go-redis/v9"
)

type Service struct {
	client *redis.Client
}

func NewService() *Service {
	logger.Info("Initialising Redis service")

	client := redis.NewClient(&redis.Options{
		Addr:     config.GetRedisURL(),
		Password: config.GetRedisPassword(),
		DB:       0,
	})

	return &Service{
		client: client,
	}
}

// Set stores a value in Redis with an optional expiration
func (s *Service) Set(ctx context.Context, key string, value interface{}, expiration time.Duration) error {
	logger.Debug("Setting Redis key: %s", key)
	return s.client.Set(ctx, key, value, expiration).Err()
}

// Get retrieves a value from Redis
func (s *Service) Get(ctx context.Context, key string) (string, error) {
	logger.Debug("Getting Redis key: %s", key)
	return s.client.Get(ctx, key).Result()
}

// Delete removes a key from Redis
func (s *Service) Delete(ctx context.Context, key string) error {
	logger.Debug("Deleting Redis key: %s", key)
	return s.client.Del(ctx, key).Err()
}

// Ping checks if Redis is accessible
func (s *Service) Ping(ctx context.Context) error {
	logger.Debug("Pinging Redis server")
	return s.client.Ping(ctx).Err()
}

// Close closes the Redis connection
func (s *Service) Close() error {
	logger.Debug("Closing Redis connection")
	return s.client.Close()
}

func IsConfigured() bool {
	logger.Debug("Checking if Redis service is configured")
	isConfigured := config.GetRedisURL() != ""

	if isConfigured {
		logger.Info("Redis service is properly configured")
	} else {
		logger.Warn("Redis service is not configured - REDIS_URL is missing")
	}

	return isConfigured
}

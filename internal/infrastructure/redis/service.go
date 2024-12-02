package redis

import (
	"context"
	"sync"
	"time"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/redis/go-redis/v9"
	"github.com/rs/zerolog/log"
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
		log.Warn().Msg("Redis URL not configured - service will be unavailable")
		return nil
	}

	client := redis.NewClient(&redis.Options{
		Addr:     url,
		Password: config.GetRedisPassword(),
		DB:       0,
	})

	if err := client.Ping(context.Background()).Err(); err != nil {
		log.Error().
			Err(err).
			Str("addr", url).
			Msg("Failed to establish Redis connection")
		return nil
	}

	return &Service{
		client: client,
	}
}

// Set stores a value in Redis with an optional expiration
func (s *Service) Set(ctx context.Context, key string, value interface{}, expiration time.Duration) error {
	if err := s.client.Set(ctx, key, value, expiration).Err(); err != nil {
		log.Error().
			Err(err).
			Str("key", key).
			Dur("expiration", expiration).
			Msg("Critical Redis SET operation failed")
		return err
	}
	return nil
}

// Get retrieves a value from Redis
func (s *Service) Get(ctx context.Context, key string) (string, error) {
	val, err := s.client.Get(ctx, key).Result()
	if err != nil && err != redis.Nil {
		log.Error().
			Err(err).
			Str("key", key).
			Msg("Critical Redis GET operation failed")
		return "", err
	}
	return val, err
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

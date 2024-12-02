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

	log.Info().
		Str("addr", url).
		Msg("Redis client initialized successfully")

	return &Service{
		client: client,
	}
}

// Set stores a value in Redis with an optional expiration
func (s *Service) Set(ctx context.Context, key string, value interface{}, expiration time.Duration) error {
	log.Info().
		Str("key", key).
		Dur("ttl", expiration).
		Msg("Setting Redis key")

	if err := s.client.Set(ctx, key, value, expiration).Err(); err != nil {
		log.Error().
			Err(err).
			Str("key", key).
			Dur("expiration", expiration).
			Msg("Critical Redis SET operation failed")
		return err
	}

	log.Debug().
		Str("key", key).
		Msg("Redis key set successfully")

	return nil
}

// Get retrieves a value from Redis
func (s *Service) Get(ctx context.Context, key string) (string, error) {
	log.Info().
		Str("key", key).
		Msg("Retrieving Redis key")

	val, err := s.client.Get(ctx, key).Result()
	if err != nil && err != redis.Nil {
		log.Error().
			Err(err).
			Str("key", key).
			Msg("Critical Redis GET operation failed")
		return "", err
	}

	log.Debug().
		Str("key", key).
		Msg("Redis key retrieved successfully")

	return val, err
}

// Delete removes a key from Redis
func (s *Service) Delete(ctx context.Context, key string) error {
	log.Info().
		Str("key", key).
		Msg("Deleting Redis key")

	if err := s.client.Del(ctx, key).Err(); err != nil {
		log.Error().
			Err(err).
			Str("key", key).
			Msg("Failed to delete Redis key")
		return err
	}

	log.Debug().
		Str("key", key).
		Msg("Redis key deleted successfully")

	return nil
}

// Ping checks if Redis is accessible
func (s *Service) Ping(ctx context.Context) error {
	log.Debug().
		Msg("Pinging Redis")

	return s.client.Ping(ctx).Err()
}

// Close closes the Redis connection
func (s *Service) Close() error {
	log.Debug().
		Msg("Closing Redis connection")

	return s.client.Close()
}

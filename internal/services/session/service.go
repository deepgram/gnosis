package session

import (
	"context"
	"encoding/json"
	"net/http"
	"sync"
	"time"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/logger"
	"github.com/deepgram/gnosis/internal/services/redis"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

const (
	sessionCookieName = "gnosis_session"
	cookieLifetime    = 1 * time.Hour
)

type SessionClaims struct {
	jwt.RegisteredClaims
	SessionID string `json:"sid"`
	UserID    string `json:"uid,omitempty"`
}

type SessionStore interface {
	Set(ctx context.Context, sessionID string, claims *SessionClaims) error
	Get(ctx context.Context, sessionID string) (*SessionClaims, error)
	Delete(ctx context.Context, sessionID string) error
}

type RedisStore struct {
	redisService *redis.Service
}

type MemoryStore struct {
	mu       sync.RWMutex
	sessions map[string]*SessionClaims
}

type Service struct {
	store SessionStore
}

func NewService() *Service {
	logger.Info("Initialising session service")

	var store SessionStore
	if redis.IsConfigured() {
		logger.Info("Using Redis for session storage")
		redisService := redis.NewService()

		// Test Redis connection
		ctx := context.Background()
		if err := redisService.Ping(ctx); err != nil {
			logger.Error("Redis connection failed: %v", err)
			logger.Warn("Falling back to in-memory session storage")
			store = newMemoryStore()
		} else {
			store = &RedisStore{redisService: redisService}
		}
	} else {
		logger.Info("Using in-memory session storage")
		store = newMemoryStore()
	}

	return &Service{store: store}
}

func newMemoryStore() *MemoryStore {
	return &MemoryStore{
		sessions: make(map[string]*SessionClaims),
	}
}

// Redis Store implementation
func (rs *RedisStore) Set(ctx context.Context, sessionID string, claims *SessionClaims) error {
	data, err := json.Marshal(claims)
	if err != nil {
		return err
	}

	return rs.redisService.Set(ctx, sessionID, string(data), cookieLifetime)
}

func (rs *RedisStore) Get(ctx context.Context, sessionID string) (*SessionClaims, error) {
	data, err := rs.redisService.Get(ctx, sessionID)
	if err != nil {
		return nil, err
	}

	var claims SessionClaims
	if err := json.Unmarshal([]byte(data), &claims); err != nil {
		return nil, err
	}

	return &claims, nil
}

func (rs *RedisStore) Delete(ctx context.Context, sessionID string) error {
	return rs.redisService.Delete(ctx, sessionID)
}

// Memory Store implementation
func (ms *MemoryStore) Set(ctx context.Context, sessionID string, claims *SessionClaims) error {
	ms.mu.Lock()
	defer ms.mu.Unlock()
	ms.sessions[sessionID] = claims
	return nil
}

func (ms *MemoryStore) Get(ctx context.Context, sessionID string) (*SessionClaims, error) {
	ms.mu.RLock()
	defer ms.mu.RUnlock()
	claims, exists := ms.sessions[sessionID]
	if !exists {
		return nil, nil
	}
	return claims, nil
}

func (ms *MemoryStore) Delete(ctx context.Context, sessionID string) error {
	ms.mu.Lock()
	defer ms.mu.Unlock()
	delete(ms.sessions, sessionID)
	return nil
}

// CreateSession generates a new session cookie and sets it in the response
func (s *Service) CreateSession(w http.ResponseWriter, userID string) error {
	logger.Debug("Creating new session for user: %s", userID)
	ctx := context.Background()

	sessionID := uuid.New().String()
	claims := &SessionClaims{
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(cookieLifetime)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			ID:        sessionID,
		},
		SessionID: sessionID,
		UserID:    userID,
	}

	if err := s.store.Set(ctx, sessionID, claims); err != nil {
		logger.Error("Failed to store session: %v", err)
		return err
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	signedToken, err := token.SignedString(config.GetJWTSecret())
	if err != nil {
		logger.Error("Failed to sign session token: %v", err)
		return err
	}

	cookie := &http.Cookie{
		Name:     sessionCookieName,
		Value:    signedToken,
		Path:     "/",
		HttpOnly: true,
		Secure:   true,
		SameSite: http.SameSiteStrictMode,
		Expires:  time.Now().Add(cookieLifetime),
	}

	http.SetCookie(w, cookie)
	logger.Info("Session cookie created successfully for user: %s", userID)
	return nil
}

// ValidateSession checks if a valid session cookie exists and returns the claims
func (s *Service) ValidateSession(r *http.Request) (*SessionClaims, error) {
	logger.Debug("Validating session cookie")
	ctx := context.Background()

	cookie, err := r.Cookie(sessionCookieName)
	if err != nil {
		if err == http.ErrNoCookie {
			logger.Debug("No session cookie found")
			return nil, nil
		}
		logger.Error("Error reading session cookie: %v", err)
		return nil, err
	}

	token, err := jwt.ParseWithClaims(cookie.Value, &SessionClaims{}, func(token *jwt.Token) (interface{}, error) {
		return config.GetJWTSecret(), nil
	})

	if err != nil {
		logger.Error("Failed to parse session token: %v", err)
		return nil, err
	}

	if claims, ok := token.Claims.(*SessionClaims); ok && token.Valid {
		// Verify session exists in store
		storedClaims, err := s.store.Get(ctx, claims.SessionID)
		if err != nil {
			logger.Error("Failed to retrieve session from store: %v", err)
			return nil, err
		}
		if storedClaims == nil {
			logger.Warn("Session not found in store")
			return nil, nil
		}

		logger.Info("Valid session found for user: %s", claims.UserID)
		return claims, nil
	}

	logger.Warn("Invalid session token")
	return nil, nil
}

// ClearSession removes the session cookie and from storage
func (s *Service) ClearSession(w http.ResponseWriter, r *http.Request) {
	logger.Debug("Clearing session cookie")
	ctx := context.Background()

	// Get session ID from cookie before clearing it
	if cookie, err := r.Cookie(sessionCookieName); err == nil {
		if token, err := jwt.ParseWithClaims(cookie.Value, &SessionClaims{}, func(token *jwt.Token) (interface{}, error) {
			return config.GetJWTSecret(), nil
		}); err == nil {
			if claims, ok := token.Claims.(*SessionClaims); ok {
				// Remove from store
				if err := s.store.Delete(ctx, claims.SessionID); err != nil {
					logger.Error("Failed to remove session from store: %v", err)
				}
			}
		}
	}

	cookie := &http.Cookie{
		Name:     sessionCookieName,
		Value:    "",
		Path:     "/",
		HttpOnly: true,
		Secure:   true,
		SameSite: http.SameSiteStrictMode,
		Expires:  time.Now().Add(-1 * time.Hour),
	}

	http.SetCookie(w, cookie)
	logger.Info("Session cookie cleared successfully")
}

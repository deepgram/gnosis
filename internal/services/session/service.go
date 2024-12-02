package session

import (
	"context"
	"encoding/json"
	"net/http"
	"sync"
	"time"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/infrastructure/redis"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

const (
	cookieLifetime = 1 * time.Hour
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

func NewService(redisService *redis.Service) *Service {

	var store SessionStore
	if redisService != nil {

		// Test Redis connection
		ctx := context.Background()
		if err := redisService.Ping(ctx); err != nil {
			store = newMemoryStore()
		} else {
			store = &RedisStore{redisService: redisService}
		}
	} else {
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
		return err
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	signedToken, err := token.SignedString(config.GetJWTSecret())
	if err != nil {
		return err
	}

	cookie := &http.Cookie{
		Name:     config.GetSessionCookieName(),
		Value:    signedToken,
		Path:     "/",
		HttpOnly: true,
		Secure:   true,
		SameSite: http.SameSiteStrictMode,
		Expires:  time.Now().Add(cookieLifetime),
	}

	http.SetCookie(w, cookie)
	return nil
}

// ValidateSession checks if a valid session cookie exists and returns the claims
func (s *Service) ValidateSession(r *http.Request) (*SessionClaims, error) {
	ctx := context.Background()

	cookie, err := r.Cookie(config.GetSessionCookieName())
	if err != nil {
		if err == http.ErrNoCookie {
			return nil, nil
		}
		return nil, err
	}

	token, err := jwt.ParseWithClaims(cookie.Value, &SessionClaims{}, func(token *jwt.Token) (interface{}, error) {
		return config.GetJWTSecret(), nil
	})

	if err != nil {
		return nil, err
	}

	if claims, ok := token.Claims.(*SessionClaims); ok && token.Valid {
		// Verify session exists in store
		storedClaims, err := s.store.Get(ctx, claims.SessionID)
		if err != nil {
			return nil, err
		}
		if storedClaims == nil {
			return nil, nil
		}

		return claims, nil
	}

	return nil, nil
}

// ClearSession removes the session cookie and from storage
func (s *Service) ClearSession(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()

	// Get session ID from cookie before clearing it
	if cookie, err := r.Cookie(config.GetSessionCookieName()); err == nil {
		if token, err := jwt.ParseWithClaims(cookie.Value, &SessionClaims{}, func(token *jwt.Token) (interface{}, error) {
			return config.GetJWTSecret(), nil
		}); err == nil {
			if claims, ok := token.Claims.(*SessionClaims); ok {
				// Remove from store
				_ = s.store.Delete(ctx, claims.SessionID)
			}
		}
	}

	cookie := &http.Cookie{
		Name:     config.GetSessionCookieName(),
		Value:    "",
		Path:     "/",
		HttpOnly: true,
		Secure:   true,
		SameSite: http.SameSiteStrictMode,
		Expires:  time.Now().Add(-1 * time.Hour),
	}

	http.SetCookie(w, cookie)
}

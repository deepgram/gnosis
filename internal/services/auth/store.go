package auth

import (
	"sync"
	"time"

	"github.com/deepgram/codename-sage/internal/logger"
	"github.com/google/uuid"
)

type Session struct {
	ID           string    `json:"id"`
	RefreshToken string    `json:"refresh_token"`
	CreatedAt    time.Time `json:"created_at"`
	ExpiresAt    time.Time `json:"expires_at"`
}

type TokenResponse struct {
	AccessToken  string `json:"access_token"`
	TokenType    string `json:"token_type"`
	ExpiresIn    int    `json:"expires_in"`
	RefreshToken string `json:"refresh_token"`
}

type TokenRequest struct {
	GrantType    string `json:"grant_type"`
	RefreshToken string `json:"refresh_token"`
}

const (
	GrantTypeAnonymous = "anonymous"
	GrantTypeRefresh   = "refresh_token"
)

type SessionStore struct {
	mu       sync.RWMutex
	sessions map[string]Session
}

func NewSessionStore() *SessionStore {
	return &SessionStore{
		sessions: make(map[string]Session),
	}
}

func (s *SessionStore) CreateSession() Session {
	logger.Info("Creating new session")
	s.mu.Lock()
	defer s.mu.Unlock()

	session := Session{
		ID:           uuid.New().String(),
		RefreshToken: uuid.New().String(),
		CreatedAt:    time.Now(),
		ExpiresAt:    time.Now().Add(24 * time.Hour), // Refresh tokens valid for 24 hours
	}

	s.sessions[session.RefreshToken] = session
	return session
}

func (s *SessionStore) GetSession(refreshToken string) (Session, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	session, exists := s.sessions[refreshToken]
	if !exists {
		logger.Warn("Session not found for refresh token")
		return Session{}, false
	}

	if time.Now().After(session.ExpiresAt) {
		logger.Warn("Expired session accessed")
		return Session{}, false
	}
	return session, true
}

func (s *SessionStore) RefreshSession(oldRefreshToken string) (Session, bool) {
	logger.Info("Attempting to refresh session")
	s.mu.Lock()
	defer s.mu.Unlock()

	oldSession, exists := s.sessions[oldRefreshToken]
	if !exists || time.Now().After(oldSession.ExpiresAt) {
		return Session{}, false
	}

	// Create new session with same ID but new refresh token
	newSession := Session{
		ID:           oldSession.ID,
		RefreshToken: uuid.New().String(),
		CreatedAt:    time.Now(),
		ExpiresAt:    time.Now().Add(24 * time.Hour),
	}

	// Remove old refresh token and store new one
	delete(s.sessions, oldRefreshToken)
	s.sessions[newSession.RefreshToken] = newSession

	logger.Info("Session refreshed successfully")
	return newSession, true
}

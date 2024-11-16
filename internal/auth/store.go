package auth

import (
	"sync"
	"time"

	"github.com/google/uuid"
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
	if !exists || time.Now().After(session.ExpiresAt) {
		return Session{}, false
	}
	return session, true
}

func (s *SessionStore) RefreshSession(oldRefreshToken string) (Session, bool) {
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

	return newSession, true
}

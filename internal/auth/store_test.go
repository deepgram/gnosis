package auth

import (
	"testing"
	"time"
)

func TestSessionStore(t *testing.T) {
	store := NewSessionStore()

	t.Run("create new session", func(t *testing.T) {
		session := store.CreateSession()

		if session.ID == "" {
			t.Error("Expected session ID to be set")
		}
		if session.RefreshToken == "" {
			t.Error("Expected refresh token to be set")
		}
		if session.CreatedAt.IsZero() {
			t.Error("Expected created at to be set")
		}
		if session.ExpiresAt.Before(time.Now()) {
			t.Error("Expected expiry to be in the future")
		}
	})

	t.Run("get valid session", func(t *testing.T) {
		session := store.CreateSession()
		retrieved, exists := store.GetSession(session.RefreshToken)

		if !exists {
			t.Error("Expected session to exist")
		}
		if retrieved.ID != session.ID {
			t.Errorf("Got session ID %s, want %s", retrieved.ID, session.ID)
		}
	})

	t.Run("get non-existent session", func(t *testing.T) {
		_, exists := store.GetSession("non-existent-token")
		if exists {
			t.Error("Expected session to not exist")
		}
	})

	t.Run("get expired session", func(t *testing.T) {
		store := NewSessionStore()
		session := store.CreateSession()

		// Manually expire the session
		store.mu.Lock()
		s := store.sessions[session.RefreshToken]
		s.ExpiresAt = time.Now().Add(-time.Hour)
		store.sessions[session.RefreshToken] = s
		store.mu.Unlock()

		_, exists := store.GetSession(session.RefreshToken)
		if exists {
			t.Error("Expected expired session to not be accessible")
		}
	})

	t.Run("refresh valid session", func(t *testing.T) {
		session := store.CreateSession()
		newSession, ok := store.RefreshSession(session.RefreshToken)

		if !ok {
			t.Error("Expected session refresh to succeed")
		}
		if newSession.ID != session.ID {
			t.Error("Session ID should remain the same after refresh")
		}
		if newSession.RefreshToken == session.RefreshToken {
			t.Error("Expected new session to have different refresh token")
		}
	})

	t.Run("refresh invalid session", func(t *testing.T) {
		_, ok := store.RefreshSession("invalid-token")
		if ok {
			t.Error("Expected session refresh to fail")
		}
	})

	t.Run("concurrent session operations", func(t *testing.T) {
		done := make(chan bool)
		for i := 0; i < 10; i++ {
			go func() {
				session := store.CreateSession()
				store.GetSession(session.RefreshToken)
				store.RefreshSession(session.RefreshToken)
				done <- true
			}()
		}

		for i := 0; i < 10; i++ {
			<-done
		}
	})
}

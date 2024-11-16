package handlers

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/deepgram/navi/internal/auth"
	"github.com/deepgram/navi/internal/config"
	"github.com/golang-jwt/jwt/v5"
	"github.com/gorilla/websocket"
)

func TestOAuthFlow(t *testing.T) {
	// Set a test-specific JWT secret
	cleanup := config.SetJWTSecret([]byte("test-secret-key-for-jwt-signing-in-tests"))
	defer cleanup()

	t.Run("anonymous authentication flow", func(t *testing.T) {
		// Request anonymous token
		reqBody := auth.TokenRequest{
			GrantType: auth.GrantTypeAnonymous,
		}
		body, err := json.Marshal(reqBody)
		if err != nil {
			t.Fatalf("Failed to marshal request: %v", err)
		}

		req := httptest.NewRequest(http.MethodPost, "/oauth/token", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		HandleToken(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
		}

		var response auth.TokenResponse
		if err := json.NewDecoder(w.Body).Decode(&response); err != nil {
			t.Fatalf("Failed to decode response: %v", err)
		}

		// Verify response structure
		if response.AccessToken == "" {
			t.Error("Access token is empty")
		}
		if response.RefreshToken == "" {
			t.Error("Refresh token is empty")
		}
		if response.TokenType != "Bearer" {
			t.Errorf("Expected token type 'Bearer', got '%s'", response.TokenType)
		}
		if response.ExpiresIn <= 0 {
			t.Error("ExpiresIn should be positive")
		}
		if response.SessionID == "" {
			t.Error("Session ID is empty")
		}

		// Verify JWT contents
		token, err := jwt.Parse(response.AccessToken, func(token *jwt.Token) (interface{}, error) {
			return config.GetJWTSecret(), nil
		})
		if err != nil {
			t.Fatalf("Failed to parse JWT: %v", err)
		}

		claims, ok := token.Claims.(jwt.MapClaims)
		if !ok {
			t.Fatal("Failed to get JWT claims")
		}

		if claims["session_id"] != response.SessionID {
			t.Error("Session ID in JWT doesn't match response")
		}

		exp, ok := claims["exp"].(float64)
		if !ok {
			t.Fatal("Expiration claim missing or invalid")
		}
		if time.Unix(int64(exp), 0).Before(time.Now()) {
			t.Error("Token is already expired")
		}
	})

	t.Run("refresh token flow", func(t *testing.T) {
		// First get an anonymous token
		anonReq := auth.TokenRequest{
			GrantType: auth.GrantTypeAnonymous,
		}
		anonBody, _ := json.Marshal(anonReq)
		anonResp := httptest.NewRecorder()
		HandleToken(anonResp, httptest.NewRequest(http.MethodPost, "/oauth/token", bytes.NewBuffer(anonBody)))

		var initialToken auth.TokenResponse
		json.NewDecoder(anonResp.Body).Decode(&initialToken)

		// Wait a moment to ensure timestamps are different
		time.Sleep(100 * time.Millisecond)

		// Now try to refresh the token
		refreshReq := auth.TokenRequest{
			GrantType:    auth.GrantTypeRefresh,
			RefreshToken: initialToken.RefreshToken,
		}
		refreshBody, _ := json.Marshal(refreshReq)

		req := httptest.NewRequest(http.MethodPost, "/oauth/token", bytes.NewBuffer(refreshBody))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		HandleToken(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
		}

		var refreshedToken auth.TokenResponse
		if err := json.NewDecoder(w.Body).Decode(&refreshedToken); err != nil {
			t.Fatalf("Failed to decode response: %v", err)
		}

		// Verify refreshed token
		if refreshedToken.AccessToken == initialToken.AccessToken {
			t.Error("Access token should be different after refresh")
		}
		if refreshedToken.RefreshToken == initialToken.RefreshToken {
			t.Error("Refresh token should be different after refresh")
		}
		if refreshedToken.SessionID != initialToken.SessionID {
			t.Error("Session ID should remain the same after refresh")
		}
	})

	t.Run("invalid refresh token", func(t *testing.T) {
		reqBody := auth.TokenRequest{
			GrantType:    auth.GrantTypeRefresh,
			RefreshToken: "invalid-refresh-token",
		}
		body, _ := json.Marshal(reqBody)

		req := httptest.NewRequest(http.MethodPost, "/oauth/token", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		HandleToken(w, req)

		if w.Code != http.StatusUnauthorized {
			t.Errorf("Expected status code %d, got %d", http.StatusUnauthorized, w.Code)
		}
	})

	t.Run("invalid grant type", func(t *testing.T) {
		reqBody := auth.TokenRequest{
			GrantType: "invalid-grant-type",
		}
		body, _ := json.Marshal(reqBody)

		req := httptest.NewRequest(http.MethodPost, "/oauth/token", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		HandleToken(w, req)

		if w.Code != http.StatusBadRequest {
			t.Errorf("Expected status code %d, got %d", http.StatusBadRequest, w.Code)
		}
	})

	t.Run("concurrent token requests", func(t *testing.T) {
		concurrentRequests := 100
		done := make(chan struct{})

		for i := 0; i < concurrentRequests; i++ {
			go func() {
				defer func() {
					done <- struct{}{}
				}()

				reqBody := auth.TokenRequest{
					GrantType: auth.GrantTypeAnonymous,
				}
				body, _ := json.Marshal(reqBody)

				req := httptest.NewRequest(http.MethodPost, "/oauth/token", bytes.NewBuffer(body))
				req.Header.Set("Content-Type", "application/json")
				w := httptest.NewRecorder()

				HandleToken(w, req)

				if w.Code != http.StatusOK {
					t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
				}

				var response auth.TokenResponse
				if err := json.NewDecoder(w.Body).Decode(&response); err != nil {
					t.Errorf("Failed to decode response: %v", err)
				}
			}()
		}

		// Wait for all requests to complete
		for i := 0; i < concurrentRequests; i++ {
			<-done
		}
	})

	t.Run("websocket connection with valid token", func(t *testing.T) {
		// Get a valid token first
		reqBody := auth.TokenRequest{
			GrantType: auth.GrantTypeAnonymous,
		}
		body, _ := json.Marshal(reqBody)

		tokenReq := httptest.NewRequest(http.MethodPost, "/oauth/token", bytes.NewBuffer(body))
		tokenReq.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		HandleToken(w, tokenReq)

		var response auth.TokenResponse
		json.NewDecoder(w.Body).Decode(&response)

		// Try to establish WebSocket connection
		wsServer := httptest.NewServer(http.HandlerFunc(HandleWebSocket))
		defer wsServer.Close()

		wsURL := "ws" + strings.TrimPrefix(wsServer.URL, "http")
		header := http.Header{}
		header.Add("Authorization", "Bearer "+response.AccessToken)

		_, resp, err := websocket.DefaultDialer.Dial(wsURL, header)
		if err != nil {
			t.Fatalf("Failed to connect to WebSocket: %v", err)
		}
		if resp.StatusCode != http.StatusSwitchingProtocols {
			t.Errorf("Expected status code %d, got %d", http.StatusSwitchingProtocols, resp.StatusCode)
		}
	})
}

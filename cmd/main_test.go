package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gorilla/websocket"
)

func TestMainServer(t *testing.T) {
	// Start test server
	server := httptest.NewServer(setupRouter())
	defer server.Close()

	t.Run("oauth token endpoint", func(t *testing.T) {
		resp, err := http.Post(server.URL+"/oauth/token", "application/json", strings.NewReader(`{
			"grant_type": "anonymous"
		}`))
		if err != nil {
			t.Fatalf("Failed to make request: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Errorf("Expected status code %d, got %d", http.StatusOK, resp.StatusCode)
		}
	})

	t.Run("websocket endpoint", func(t *testing.T) {
		// First get a valid token
		resp, err := http.Post(server.URL+"/oauth/token", "application/json", strings.NewReader(`{
			"grant_type": "anonymous"
		}`))
		if err != nil {
			t.Fatalf("Failed to get token: %v", err)
		}

		var tokenResp struct {
			AccessToken string `json:"access_token"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&tokenResp); err != nil {
			t.Fatalf("Failed to decode token response: %v", err)
		}
		resp.Body.Close()

		// Connect to WebSocket
		wsURL := "ws" + strings.TrimPrefix(server.URL, "http") + "/ws"
		header := http.Header{}
		header.Add("Authorization", "Bearer "+tokenResp.AccessToken)

		ws, _, err := websocket.DefaultDialer.Dial(wsURL, header)
		if err != nil {
			t.Fatalf("Failed to connect to WebSocket: %v", err)
		}
		defer ws.Close()

		// Read welcome message
		_, msg, err := ws.ReadMessage()
		if err != nil {
			t.Fatalf("Failed to read message: %v", err)
		}
		if string(msg) != "Connected" {
			t.Errorf("Expected 'Connected' message, got: %s", string(msg))
		}
	})

	t.Run("invalid endpoint", func(t *testing.T) {
		resp, err := http.Get(server.URL + "/invalid")
		if err != nil {
			t.Fatalf("Failed to make request: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusNotFound {
			t.Errorf("Expected status code %d, got %d", http.StatusNotFound, resp.StatusCode)
		}
	})
}

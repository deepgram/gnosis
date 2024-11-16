package handlers

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/deepgram/navi/internal/auth"
	"github.com/gorilla/websocket"
)

func TestWebSocketPingPong(t *testing.T) {
	// Set shorter timeouts for testing
	testTimeouts := TimeoutConfig{
		PongWait:   3 * time.Second,
		PingPeriod: 1 * time.Second,
		WriteWait:  1 * time.Second,
	}

	// Reset timeouts after test
	cleanup := SetTimeouts(testTimeouts)
	defer cleanup()

	// Create test servers
	wsServer := httptest.NewServer(http.HandlerFunc(HandleWebSocket))
	defer wsServer.Close()

	// Get a valid token first
	reqBody := auth.TokenRequest{
		GrantType: auth.GrantTypeAnonymous,
	}
	body, _ := json.Marshal(reqBody)

	tokenReq := httptest.NewRequest(http.MethodPost, "/oauth/token", bytes.NewBuffer(body))
	tokenReq.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	HandleToken(w, tokenReq)

	var tokenResp auth.TokenResponse
	json.NewDecoder(w.Body).Decode(&tokenResp)

	wsURL := "ws" + strings.TrimPrefix(wsServer.URL, "http")

	t.Run("connection times out when no pong response", func(t *testing.T) {
		header := http.Header{}
		header.Add("Authorization", "Bearer "+tokenResp.AccessToken)

		conn, _, err := websocket.DefaultDialer.Dial(wsURL, header)
		if err != nil {
			t.Fatalf("Failed to connect to WebSocket: %v", err)
		}
		defer conn.Close()

		// Read initial message
		_, msg, err := conn.ReadMessage()
		if err != nil {
			t.Fatalf("Failed to read initial message: %v", err)
		}
		if string(msg) != "Connected" {
			t.Errorf("Expected 'Connected' message, got: %s", string(msg))
		}

		// Wait for connection to timeout
		time.Sleep(testTimeouts.PongWait + 500*time.Millisecond)

		// Try to read - should fail due to timeout
		_, _, err = conn.ReadMessage()
		if err == nil {
			t.Error("Expected connection to be closed due to ping timeout")
		}
	})

	t.Run("connection stays alive with pong responses", func(t *testing.T) {
		header := http.Header{}
		header.Add("Authorization", "Bearer "+tokenResp.AccessToken)

		conn, _, err := websocket.DefaultDialer.Dial(wsURL, header)
		if err != nil {
			t.Fatalf("Failed to connect to WebSocket: %v", err)
		}
		defer conn.Close()

		// Set up ping handler that responds with pong
		conn.SetPingHandler(func(appData string) error {
			return conn.WriteControl(websocket.PongMessage, []byte{}, time.Now().Add(testTimeouts.WriteWait))
		})

		// Read initial message
		_, msg, err := conn.ReadMessage()
		if err != nil {
			t.Fatalf("Failed to read initial message: %v", err)
		}
		if string(msg) != "Connected" {
			t.Errorf("Expected 'Connected' message, got: %s", string(msg))
		}

		// Test message exchange
		testMessage := func(i int) error {
			testMsg := []byte(fmt.Sprintf("test-%d", i))

			if err := conn.SetWriteDeadline(time.Now().Add(testTimeouts.WriteWait)); err != nil {
				return fmt.Errorf("failed to set write deadline: %v", err)
			}

			if err := conn.WriteMessage(websocket.TextMessage, testMsg); err != nil {
				return fmt.Errorf("failed to write message: %v", err)
			}

			if err := conn.SetReadDeadline(time.Now().Add(testTimeouts.PongWait)); err != nil {
				return fmt.Errorf("failed to set read deadline: %v", err)
			}

			_, response, err := conn.ReadMessage()
			if err != nil {
				return fmt.Errorf("failed to read response: %v", err)
			}

			if string(response) != string(testMsg) {
				return fmt.Errorf("expected echo response '%s', got: %s", testMsg, response)
			}

			return nil
		}

		// Send a few test messages with delays between them
		for i := 0; i < 3; i++ {
			time.Sleep(testTimeouts.PingPeriod / 2)
			if err := testMessage(i); err != nil {
				t.Fatalf("Message exchange %d failed: %v", i, err)
			}
		}
	})
}

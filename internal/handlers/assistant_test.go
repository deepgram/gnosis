package handlers

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/deepgram/navi/internal/assistant"
	"github.com/deepgram/navi/internal/connections"
	"github.com/gorilla/websocket"
)

func TestHandleAssistantMessage(t *testing.T) {
	// Set shorter timeouts for testing
	testTimeouts := connections.TimeoutConfig{
		PongWait:   100 * time.Millisecond,
		PingPeriod: 50 * time.Millisecond,
		WriteWait:  50 * time.Millisecond,
	}

	// Create test server and client connection
	wsServer := httptest.NewServer(http.HandlerFunc(HandleWebSocket))
	defer wsServer.Close()

	// Get a valid token first
	tokenResp := getValidToken(t)

	wsURL := "ws" + strings.TrimPrefix(wsServer.URL, "http")

	t.Run("valid message handling", func(t *testing.T) {
		// Create a context with timeout
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()

		header := http.Header{}
		header.Add("Authorization", "Bearer "+tokenResp)

		// Create dialer with context
		dialer := websocket.Dialer{
			HandshakeTimeout: time.Second,
		}

		conn, _, err := dialer.DialContext(ctx, wsURL, header)
		if err != nil {
			t.Fatalf("Failed to connect to WebSocket: %v", err)
		}

		// Ensure connection is closed after test
		defer func() {
			conn.WriteControl(websocket.CloseMessage,
				websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""),
				time.Now().Add(testTimeouts.WriteWait))
			conn.Close()
		}()

		// Read initial "Connected" message
		_, msg, err := conn.ReadMessage()
		if err != nil {
			t.Fatalf("Failed to read initial message: %v", err)
		}
		if string(msg) != "Connected" {
			t.Errorf("Expected 'Connected' message, got: %s", string(msg))
		}

		// Send test message
		testMsg := assistant.UserMessage{
			Content:   "Hello assistant",
			MessageID: "test-123",
		}

		if err := conn.WriteJSON(testMsg); err != nil {
			t.Fatalf("Failed to write message: %v", err)
		}

		// Read streaming response
		var streamResp assistant.AssistantResponse
		if err := conn.ReadJSON(&streamResp); err != nil {
			t.Fatalf("Failed to read streaming response: %v", err)
		}
		if streamResp.Status != assistant.StatusStreaming {
			t.Errorf("Expected streaming status, got %s", streamResp.Status)
		}

		// Read complete response
		var completeResp assistant.AssistantResponse
		if err := conn.ReadJSON(&completeResp); err != nil {
			t.Fatalf("Failed to read complete response: %v", err)
		}

		if completeResp.Status != assistant.StatusComplete {
			t.Errorf("Expected complete status, got %s", completeResp.Status)
		}
		if completeResp.MessageID != testMsg.MessageID {
			t.Errorf("Expected message ID %s, got %s", testMsg.MessageID, completeResp.MessageID)
		}
	})

	t.Run("invalid message format", func(t *testing.T) {
		// Create a context with timeout
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()

		header := http.Header{}
		header.Add("Authorization", "Bearer "+tokenResp)

		// Create dialer with context
		dialer := websocket.Dialer{
			HandshakeTimeout: time.Second,
		}

		conn, _, err := dialer.DialContext(ctx, wsURL, header)
		if err != nil {
			t.Fatalf("Failed to connect to WebSocket: %v", err)
		}

		// Ensure connection is closed after test
		defer func() {
			conn.WriteControl(websocket.CloseMessage,
				websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""),
				time.Now().Add(testTimeouts.WriteWait))
			conn.Close()
		}()

		// Read initial "Connected" message
		_, msg, err := conn.ReadMessage()
		if err != nil {
			t.Fatalf("Failed to read initial message: %v", err)
		}
		if string(msg) != "Connected" {
			t.Errorf("Expected 'Connected' message, got: %s", string(msg))
		}

		// Send invalid JSON
		err = conn.WriteMessage(websocket.TextMessage, []byte("invalid json"))
		if err != nil {
			t.Fatalf("Failed to write message: %v", err)
		}

		// Should receive error response
		var errorResp assistant.AssistantResponse
		err = conn.ReadJSON(&errorResp)
		if err != nil {
			t.Fatalf("Failed to read error response: %v", err)
		}

		if errorResp.Status != assistant.StatusError {
			t.Errorf("Expected error status, got %s", errorResp.Status)
		}
	})
}

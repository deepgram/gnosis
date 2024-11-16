package handlers

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/deepgram/navi/internal/auth"
	"github.com/deepgram/navi/internal/connections"
	"github.com/gorilla/websocket"
)

func TestWebSocketPingPong(t *testing.T) {
	// Set shorter timeouts for testing
	testTimeouts := connections.TimeoutConfig{
		PongWait:   100 * time.Millisecond,
		PingPeriod: 50 * time.Millisecond,
		WriteWait:  50 * time.Millisecond,
	}

	// Create test manager with custom timeouts
	manager = connections.NewManager(testTimeouts)

	// Create test server
	wsServer := httptest.NewServer(http.HandlerFunc(HandleWebSocket))
	defer wsServer.Close()

	// Get a valid token first
	tokenResp := getValidToken(t)

	wsURL := "ws" + strings.TrimPrefix(wsServer.URL, "http")

	t.Run("connection times out when no pong response", func(t *testing.T) {
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

		// Create done channel for cleanup
		done := make(chan struct{})
		defer close(done)

		// Ensure connection is closed after test
		defer func() {
			select {
			case <-ctx.Done():
				// Context timeout, force close
				conn.Close()
			default:
				// Normal close
				conn.WriteControl(websocket.CloseMessage,
					websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""),
					time.Now().Add(testTimeouts.WriteWait))
				conn.Close()
			}
		}()

		// Read initial message with timeout
		err = conn.SetReadDeadline(time.Now().Add(testTimeouts.PongWait))
		if err != nil {
			t.Fatalf("Failed to set read deadline: %v", err)
		}

		_, msg, err := conn.ReadMessage()
		if err != nil {
			t.Fatalf("Failed to read initial message: %v", err)
		}
		if string(msg) != "Connected" {
			t.Errorf("Expected 'Connected' message, got: %s", string(msg))
		}

		// Wait for connection to timeout
		waitChan := make(chan error)
		go func() {
			_, _, err := conn.ReadMessage()
			waitChan <- err
		}()

		select {
		case err := <-waitChan:
			if err == nil {
				t.Error("Expected connection to be closed due to ping timeout")
			}
			if !websocket.IsCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) &&
				!strings.Contains(err.Error(), "timeout") {
				t.Errorf("Expected timeout or close error, got: %v", err)
			}
		case <-ctx.Done():
			t.Fatal("Test timed out waiting for connection to close")
		}
	})

	t.Run("connection stays alive with pong responses", func(t *testing.T) {
		header := http.Header{}
		header.Add("Authorization", "Bearer "+tokenResp)

		conn, _, err := websocket.DefaultDialer.Dial(wsURL, header)
		if err != nil {
			t.Fatalf("Failed to connect to WebSocket: %v", err)
		}

		// Ensure connection is closed after test
		defer func() {
			conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""))
			conn.Close()
		}()

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

func TestTokenExtraction(t *testing.T) {
	tests := []struct {
		name        string
		headerValue string
		want        string
	}{
		{
			name:        "valid bearer token",
			headerValue: "Bearer test-token",
			want:        "test-token",
		},
		{
			name:        "missing bearer prefix",
			headerValue: "test-token",
			want:        "",
		},
		{
			name:        "empty header",
			headerValue: "",
			want:        "",
		},
		{
			name:        "invalid format",
			headerValue: "Bearer",
			want:        "",
		},
		{
			name:        "malformed with extra spaces",
			headerValue: "Bearer  test-token  ",
			want:        "",
		},
		{
			name:        "wrong auth type",
			headerValue: "Basic test-token",
			want:        "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodGet, "/", nil)
			if tt.headerValue != "" {
				req.Header.Set("Authorization", tt.headerValue)
			}

			got := extractToken(req)
			if got != tt.want {
				t.Errorf("extractToken() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestWebSocketConnectionErrors(t *testing.T) {
	// Create test server
	wsServer := httptest.NewServer(http.HandlerFunc(HandleWebSocket))
	defer wsServer.Close()

	// Get a valid token for some tests
	validToken := getValidToken(t)

	tests := []struct {
		name          string
		setupRequest  func() (*http.Header, string)
		expectedError string
		expectedClose bool
	}{
		{
			name: "missing authorization header",
			setupRequest: func() (*http.Header, string) {
				header := http.Header{}
				wsURL := "ws" + strings.TrimPrefix(wsServer.URL, "http")
				return &header, wsURL
			},
			expectedError: "websocket: bad handshake",
			expectedClose: true,
		},
		{
			name: "invalid token",
			setupRequest: func() (*http.Header, string) {
				header := http.Header{
					"Authorization": []string{"Bearer invalid-token"},
				}
				wsURL := "ws" + strings.TrimPrefix(wsServer.URL, "http")
				return &header, wsURL
			},
			expectedError: "websocket: bad handshake",
			expectedClose: true,
		},
		{
			name: "duplicate header upgrade request",
			setupRequest: func() (*http.Header, string) {
				header := http.Header{
					"Authorization": []string{"Bearer " + validToken},
					"Connection":    []string{"Invalid"},
				}
				wsURL := "ws" + strings.TrimPrefix(wsServer.URL, "http")
				return &header, wsURL
			},
			expectedError: "websocket: duplicate header not allowed: Connection",
			expectedClose: true,
		},
		{
			name: "malformed upgrade request",
			setupRequest: func() (*http.Header, string) {
				header := http.Header{
					"Authorization":         []string{"Bearer " + validToken},
					"Sec-WebSocket-Version": []string{"invalid"},
				}
				wsURL := "ws" + strings.TrimPrefix(wsServer.URL, "http")
				return &header, wsURL
			},
			expectedError: "websocket: bad handshake",
			expectedClose: true,
		},
		{
			name: "invalid websocket URL",
			setupRequest: func() (*http.Header, string) {
				header := http.Header{
					"Authorization": []string{"Bearer " + validToken},
				}
				return &header, "ws://invalid-url:9999"
			},
			expectedError: "dial tcp",
			expectedClose: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			header, wsURL := tt.setupRequest()

			// Attempt to connect
			c, _, err := websocket.DefaultDialer.Dial(wsURL, *header)

			// Check if we expect an error
			if tt.expectedError != "" {
				if err == nil {
					t.Error("Expected an error but got none")
				} else if !strings.Contains(err.Error(), tt.expectedError) {
					t.Errorf("Expected error containing %q, got %q", tt.expectedError, err.Error())
				}
			} else if err != nil {
				t.Errorf("Unexpected error: %v", err)
			}

			// Clean up if connection was established
			if c != nil {
				c.Close()
			}
		})
	}
}

// Helper function to get a valid token for testing
func getValidToken(t *testing.T) string {
	reqBody := auth.TokenRequest{
		GrantType: auth.GrantTypeAnonymous,
	}
	body, _ := json.Marshal(reqBody)

	req := httptest.NewRequest(http.MethodPost, "/oauth/token", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	HandleToken(w, req)

	var response auth.TokenResponse
	if err := json.NewDecoder(w.Body).Decode(&response); err != nil {
		t.Fatalf("Failed to decode token response: %v", err)
	}

	return response.AccessToken
}

// Optional: Add test for connection timeout
func TestWebSocketConnectionTimeout(t *testing.T) {
	// Set very short timeout for testing
	originalTimeout := websocket.DefaultDialer.HandshakeTimeout
	websocket.DefaultDialer.HandshakeTimeout = 100 * time.Millisecond
	defer func() {
		websocket.DefaultDialer.HandshakeTimeout = originalTimeout
	}()

	// Create a server that sleeps longer than the timeout
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(200 * time.Millisecond)
		HandleWebSocket(w, r)
	}))
	defer server.Close()

	// Attempt connection
	header := http.Header{
		"Authorization": []string{"Bearer " + getValidToken(t)},
	}
	wsURL := "ws" + strings.TrimPrefix(server.URL, "http")

	_, _, err := websocket.DefaultDialer.Dial(wsURL, header)
	if err == nil {
		t.Error("Expected timeout error but got none")
	} else if !strings.Contains(err.Error(), "timeout") {
		t.Errorf("Expected timeout error, got: %v", err)
	}
}

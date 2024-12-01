package websocket

import (
	"net/http"
	"net/url"
	"os"
	"sync"

	"github.com/deepgram/gnosis/pkg/logger"
	"github.com/gorilla/websocket"
)

var (
	upgrader = websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool {
			logger.Debug(logger.HANDLER, "Checking WebSocket origin: %s", r.Header.Get("Origin"))
			// TODO: Implement proper origin checking based on configuration
			return true
		},
	}
)

// HandleAgentWebSocket handles the voice agent WebSocket proxy connection
func HandleAgentWebSocket(w http.ResponseWriter, r *http.Request) {
	logger.Info(logger.HANDLER, "New WebSocket connection request from %s", r.RemoteAddr)

	// Upgrade client connection to WebSocket
	clientConn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		logger.Error(logger.HANDLER, "Failed to upgrade client connection from %s: %v", r.RemoteAddr, err)
		return
	}
	defer clientConn.Close()
	logger.Info(logger.HANDLER, "Successfully upgraded connection to WebSocket for %s", r.RemoteAddr)

	// Connect to the target WebSocket server
	targetURL := "wss://agent.deepgram.com/agent"
	u, err := url.Parse(targetURL)
	if err != nil {
		logger.Error(logger.HANDLER, "Invalid target URL %s: %v", targetURL, err)
		return
	}
	logger.Debug(logger.HANDLER, "Attempting to connect to target WebSocket server: %s", targetURL)

	// Write the bearer token to the header from environment variables
	token := os.Getenv("DEEPGRAM_API_KEY")
	if token == "" {
		logger.Fatal(logger.HANDLER, "DEEPGRAM_API_KEY environment variable not set")
		return
	}

	header := http.Header{}
	header.Add("Authorization", "token "+token)
	logger.Debug(logger.HANDLER, "Added authorization header for target connection")

	serverConn, resp, err := websocket.DefaultDialer.Dial(u.String(), header)
	if err != nil {
		if resp != nil {
			logger.Error(logger.HANDLER, "Failed to connect to target server. Status: %d, Error: %v", resp.StatusCode, err)
		} else {
			logger.Error(logger.HANDLER, "Failed to connect to target server: %v", err)
		}
		return
	}
	defer serverConn.Close()
	logger.Info(logger.HANDLER, "Successfully established connection to target WebSocket server")

	// Channels for coordinating shutdown
	errChan := make(chan error, 2)
	done := make(chan struct{})
	var closeOnce sync.Once

	cleanup := func() {
		closeOnce.Do(func() {
			logger.Info(logger.HANDLER, "Initiating WebSocket connection cleanup")
			close(done)
			clientConn.Close()
			serverConn.Close()
			logger.Debug(logger.HANDLER, "WebSocket connections closed and cleanup complete")
		})
	}
	defer cleanup()

	// Start goroutine to forward client -> server
	logger.Debug(logger.HANDLER, "Starting client -> server message forwarding")
	go proxyMessages(clientConn, serverConn, "Client -> Server", done, errChan)

	// Start goroutine to forward server -> client
	logger.Debug(logger.HANDLER, "Starting server -> client message forwarding")
	go proxyMessages(serverConn, clientConn, "Server -> Client", done, errChan)

	// Wait for an error or connection closure
	err = <-errChan
	if err != nil {
		if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
			logger.Error(logger.HANDLER, "Unexpected WebSocket closure: %v", err)
		} else {
			logger.Info(logger.HANDLER, "WebSocket connection closed normally: %v", err)
		}
	}
}

func proxyMessages(src, dst *websocket.Conn, direction string, done chan struct{}, errChan chan error) {
	logger.Debug(logger.HANDLER, "Starting message proxy routine for %s", direction)

	for {
		select {
		case <-done:
			logger.Debug(logger.HANDLER, "Stopping message proxy routine for %s", direction)
			return
		default:
			messageType, msg, err := src.ReadMessage()
			if err != nil {
				if websocket.IsCloseError(err, websocket.CloseNormalClosure) {
					logger.Info(logger.HANDLER, "%s: Normal connection closure", direction)
				} else {
					logger.Warn(logger.HANDLER, "%s: Error reading message: %v", direction, err)
				}
				errChan <- err
				return
			}

			// Log message details based on type
			switch messageType {
			case websocket.TextMessage:
				logger.Debug(logger.HANDLER, "%s: Text message received (%d bytes)", direction, len(msg))
			case websocket.BinaryMessage:
				logger.Debug(logger.HANDLER, "%s: Binary message received (%d bytes)", direction, len(msg))
			case websocket.CloseMessage:
				logger.Info(logger.HANDLER, "%s: Close message received", direction)
			case websocket.PingMessage:
				logger.Debug(logger.HANDLER, "%s: Ping message received", direction)
			case websocket.PongMessage:
				logger.Debug(logger.HANDLER, "%s: Pong message received", direction)
			default:
				logger.Warn(logger.HANDLER, "%s: Unknown message type received: %d", direction, messageType)
			}

			if err := dst.WriteMessage(messageType, msg); err != nil {
				logger.Error(logger.HANDLER, "%s: Failed to write message: %v", direction, err)
				errChan <- err
				return
			}
			logger.Debug(logger.HANDLER, "%s: Successfully forwarded message", direction)
		}
	}
}

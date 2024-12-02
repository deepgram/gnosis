package websocket

import (
	"net/http"
	"net/url"
	"os"
	"sync"

	"github.com/gorilla/websocket"
	"github.com/rs/zerolog/log"
)

var (
	upgrader = websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool {
			// TODO: Implement proper origin checking based on configuration
			return true
		},
	}
)

// HandleAgentWebSocket handles the voice agent WebSocket proxy connection
func HandleAgentWebSocket(w http.ResponseWriter, r *http.Request) {
	// Upgrade client connection to WebSocket
	clientConn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Warn().Err(err).Msg("Failed to upgrade client connection to WebSocket")
		return
	}
	defer clientConn.Close()

	// Connect to the target WebSocket server
	targetURL := "wss://agent.deepgram.com/agent"
	u, err := url.Parse(targetURL)
	if err != nil {
		log.Warn().Str("url", targetURL).Err(err).Msg("Client provided invalid target URL")
		return
	}

	// Write the bearer token to the header from environment variables
	token := os.Getenv("DEEPGRAM_API_KEY")
	if token == "" {
		log.Warn().Msg("WebSocket connection attempted without API key configured")
		return
	}

	log.Info().
		Str("client_ip", r.RemoteAddr).
		Str("target_url", targetURL).
		Msg("Client WebSocket connection established")

	header := http.Header{}
	header.Add("Authorization", "token "+token)

	serverConn, resp, err := websocket.DefaultDialer.Dial(u.String(), header)
	if err != nil {
		if resp != nil {
			log.Error().Int("status", resp.StatusCode).Err(err).Msg("Failed to connect to target server")
		} else {
			log.Error().Err(err).Msg("Failed to connect to target server")
		}
		return
	}
	defer serverConn.Close()

	log.Info().
		Str("client_ip", r.RemoteAddr).
		Str("target_url", targetURL).
		Msg("Connected to target WebSocket server")

	// Channels for coordinating shutdown
	errChan := make(chan error, 2)
	done := make(chan struct{})
	var closeOnce sync.Once

	cleanup := func() {
		closeOnce.Do(func() {
			close(done)
			clientConn.Close()
			serverConn.Close()
		})
	}
	defer cleanup()

	log.Info().
		Str("client_ip", r.RemoteAddr).
		Msg("Starting WebSocket message relay")

	// Start goroutine to forward client -> server
	go proxyMessages(clientConn, serverConn, "Client -> Server", done, errChan)

	// Start goroutine to forward server -> client
	go proxyMessages(serverConn, clientConn, "Server -> Client", done, errChan)

	// Wait for an error or connection closure
	err = <-errChan
	if err != nil {
		if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
			log.Error().Err(err).Msg("Unexpected WebSocket closure")
		} else {
			log.Info().
				Str("client_ip", r.RemoteAddr).
				Msg("WebSocket connection closed gracefully")
		}
	}
}

func proxyMessages(src, dst *websocket.Conn, direction string, done chan struct{}, errChan chan error) {
	for {
		select {
		case <-done:
			return
		default:
			messageType, msg, err := src.ReadMessage()
			if err != nil {
				if !websocket.IsCloseError(err, websocket.CloseNormalClosure) {
					log.Error().Str("direction", direction).Err(err).Msg("Error in proxy")
				}
				errChan <- err
				return
			}

			if err := dst.WriteMessage(messageType, msg); err != nil {
				errChan <- err
				return
			}
		}
	}
}

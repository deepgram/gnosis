package websocket

import (
	"log"
	"net/http"
	"net/url"
	"os"
	"sync"

	"github.com/gorilla/websocket"
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
		return
	}
	defer clientConn.Close()

	// Connect to the target WebSocket server
	targetURL := "wss://agent.deepgram.com/agent"
	u, err := url.Parse(targetURL)
	if err != nil {
		log.Printf("Invalid target URL %s: %v", targetURL, err)
		return
	}

	// Write the bearer token to the header from environment variables
	token := os.Getenv("DEEPGRAM_API_KEY")
	if token == "" {
		log.Fatal("DEEPGRAM_API_KEY environment variable not set")
		return
	}

	header := http.Header{}
	header.Add("Authorization", "token "+token)

	serverConn, resp, err := websocket.DefaultDialer.Dial(u.String(), header)
	if err != nil {
		if resp != nil {
			log.Printf("Failed to connect to target server. Status: %d, Error: %v", resp.StatusCode, err)
		} else {
			log.Printf("Failed to connect to target server: %v", err)
		}
		return
	}
	defer serverConn.Close()

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

	// Start goroutine to forward client -> server
	go proxyMessages(clientConn, serverConn, "Client -> Server", done, errChan)

	// Start goroutine to forward server -> client
	go proxyMessages(serverConn, clientConn, "Server -> Client", done, errChan)

	// Wait for an error or connection closure
	err = <-errChan
	if err != nil {
		if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
			log.Printf("Unexpected WebSocket closure: %v", err)
		} else {
			log.Printf("WebSocket connection closed normally: %v", err)
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
					log.Printf("Error in %s: %v", direction, err)
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

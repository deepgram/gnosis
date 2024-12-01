package main

import (
	"log"
	"net/http"
	"net/url"
	"os"
	"sync"
	"time"

	v1handlers "github.com/deepgram/gnosis/internal/api/v1/handlers"
	"github.com/deepgram/gnosis/internal/services"
	"github.com/deepgram/gnosis/pkg/logger"
	"github.com/gorilla/mux"
	"github.com/gorilla/websocket"
)

var (
	upgrader = websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool {
			// Allow all origins for simplicity; customize as needed.
			return true
		},
	}
)

// proxyWebSocket handles bidirectional WebSocket proxying.
func proxyWebSocket(w http.ResponseWriter, r *http.Request) {
	// Upgrade client connection to WebSocket.
	clientConn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("Failed to upgrade client connection: %v", err)
		return
	}
	defer clientConn.Close()

	// Connect to the target WebSocket server.
	targetURL := "wss://sts.sandbox.deepgram.com/agent"
	u, err := url.Parse(targetURL)
	if err != nil {
		log.Printf("Invalid target URL: %v", err)
		return
	}

	// Add authorization header to the connection request
	header := http.Header{}
	header.Add("Authorization", "Token "+os.Getenv("DEEPGRAM_API_KEY"))

	serverConn, _, err := websocket.DefaultDialer.Dial(u.String(), header)
	if err != nil {
		log.Printf("Failed to connect to target WebSocket server: %v", err)
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
	go func() {
		for {
			select {
			case <-done:
				return
			default:
				messageType, msg, err := clientConn.ReadMessage()
				if err != nil {
					errChan <- err
					return
				}

				// Log the message based on type
				switch messageType {
				case websocket.TextMessage:
					logger.Debug(logger.APP, "Client -> Server: %s", string(msg))
				case websocket.BinaryMessage:
					logger.Debug(logger.APP, "Client -> Server: [binary data]")
				case websocket.CloseMessage:
					logger.Debug(logger.APP, "Client -> Server: [close message]")
				case websocket.PingMessage:
					logger.Debug(logger.APP, "Client -> Server: [ping]")
				case websocket.PongMessage:
					logger.Debug(logger.APP, "Client -> Server: [pong]")
				}

				err = serverConn.WriteMessage(messageType, msg)
				if err != nil {
					errChan <- err
					return
				}
			}
		}
	}()

	// Start goroutine to forward server -> client
	go func() {
		for {
			select {
			case <-done:
				return
			default:
				messageType, msg, err := serverConn.ReadMessage()
				if err != nil {
					errChan <- err
					return
				}

				// Log the message based on type
				switch messageType {
				case websocket.TextMessage:
					logger.Debug(logger.APP, "Server -> Client: %s", string(msg))
				case websocket.BinaryMessage:
					logger.Debug(logger.APP, "Server -> Client: [binary data]")
				case websocket.CloseMessage:
					logger.Debug(logger.APP, "Server -> Client: [close message]")
				case websocket.PingMessage:
					logger.Debug(logger.APP, "Server -> Client: [ping]")
				case websocket.PongMessage:
					logger.Debug(logger.APP, "Server -> Client: [pong]")
				}

				err = clientConn.WriteMessage(messageType, msg)
				if err != nil {
					errChan <- err
					return
				}
			}
		}
	}()

	// Wait for an error or connection closure
	err = <-errChan
	if err != nil && websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
		logger.Error(logger.APP, "WebSocket proxy error: %v", err)
	}
}

func main() {
	logger.Info(logger.APP, "Starting Gnosis server")

	// Initialize services
	services, err := services.InitializeServices()
	if err != nil {
		logger.Fatal(logger.APP, "Failed to initialize services: %v", err)
		os.Exit(1)
	}

	// Setup router
	logger.Debug(logger.APP, "Setting up router")
	r := mux.NewRouter()

	// websocket proxy
	r.HandleFunc("/ws", proxyWebSocket)

	/**
	 * Register all V1 routes
	 *	/v1/oauth/token
	 *	/v1/oauth/widget
	 *	/v1/widget.js
	 *	/v1/chat/completions
	 */
	v1handlers.RegisterV1Routes(r, services)

	// Configure server
	srv := &http.Server{
		Addr:         ":8080",
		Handler:      r,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Start server
	logger.Info(logger.APP, "Server starting on :8080")
	if err := srv.ListenAndServe(); err != nil {
		logger.Fatal(logger.APP, "Server failed: %v", err)
	}
}

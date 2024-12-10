package websocket

import (
	"bytes"
	"io"
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
			return true
		},
	}
)

func HandleAgentWebSocket(w http.ResponseWriter, r *http.Request) {
	clientConn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	defer clientConn.Close()

	targetURL := "wss://agent.deepgram.com/agent"
	u, err := url.Parse(targetURL)
	if err != nil {
		return
	}

	token := os.Getenv("DEEPGRAM_API_KEY")
	if token == "" {
		return
	}

	header := http.Header{}
	header.Add("Authorization", "token "+token)

	serverConn, _, err := websocket.DefaultDialer.Dial(u.String(), header)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to connect to Deepgram agent server")
		return
	}
	defer serverConn.Close()

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

	go proxyMessages("upstream", clientConn, serverConn, done, errChan)
	go proxyMessages("downstream", serverConn, clientConn, done, errChan)

	err = <-errChan
	if err != nil {
		if !websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
			return
		}
	}
}

func proxyMessages(_ string, src, dst *websocket.Conn, done chan struct{}, errChan chan error) {
	for {
		select {
		case <-done:
			return
		default:
			messageType, reader, err := src.NextReader()
			if err != nil {
				errChan <- err
				return
			}

			// Create a buffer to store message content
			var buf bytes.Buffer
			tee := io.TeeReader(reader, &buf)

			// Create writer for destination
			writer, err := dst.NextWriter(messageType)
			if err != nil {
				errChan <- err
				return
			}

			// Copy message to both buffer and destination
			if _, err := io.Copy(writer, tee); err != nil {
				writer.Close()
				errChan <- err
				return
			}

			// Log the message content
			if messageType != websocket.BinaryMessage {
				log.Debug().
					Int("message_type", messageType).
					Str("content", buf.String()).
					Msg("Proxied WebSocket text message")
			}

			if err := writer.Close(); err != nil {
				errChan <- err
				return
			}
		}
	}
}

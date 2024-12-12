package websocket

import (
	"bufio"
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

// MessageHandler defines the function signature for message handlers
type MessageHandler func(messageType int, bufferedReader *bufio.Reader, reader io.Reader, writer io.Writer) (int64, error)

// messageHandlers maps message prefixes to their handler functions
var messageHandlers = map[string]MessageHandler{
	string([]byte(`{"type":"SettingsC`)): HandleSettingsConfigurationMessage,
	string([]byte(`{"type":"Error"`)):    HandleErrorMessage,
}

var HandleSettingsConfigurationMessage MessageHandler = func(messageType int, bufferedReader *bufio.Reader, reader io.Reader, writer io.Writer) (int64, error) {
	log.Debug().
		Str("type", "SettingsConfiguration").
		Msg("Processing settings configuration message")

	return io.Copy(writer, reader)
}

var HandleErrorMessage MessageHandler = func(messageType int, bufferedReader *bufio.Reader, reader io.Reader, writer io.Writer) (int64, error) {
	log.Debug().
		Str("type", "ErrorMessage").
		Msg("Processing error message")

	return io.Copy(writer, reader)
}

var HandleDefaultMessage MessageHandler = func(messageType int, bufferedReader *bufio.Reader, reader io.Reader, writer io.Writer) (int64, error) {
	log.Debug().
		Msg("Processing default message")

	return io.Copy(writer, reader)
}

// HandleMessage processes a message based on its type prefix
func HandleMessage(messageType int, reader io.Reader, writer io.Writer) (int64, error) {
	bufferedReader := bufio.NewReader(reader)

	// Peek at the first few bytes of the message to see if it matches any of the message handlers
	for prefix, handler := range messageHandlers {
		peek, err := bufferedReader.Peek(len(prefix))

		if err == nil && bytes.Equal(peek, []byte(prefix)) {
			return handler(messageType, bufferedReader, reader, writer)
		}
	}

	return HandleDefaultMessage(messageType, bufferedReader, reader, writer)
}

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

			// Create writer for destination
			writer, err := dst.NextWriter(messageType)
			if err != nil {
				errChan <- err
				return
			}

			if _, err := io.Copy(writer, reader); err != nil {
				// if _, err := HandleMessage(messageType, reader, writer); err != nil {
				writer.Close()
				errChan <- err
				return
			}

			if err := writer.Close(); err != nil {
				errChan <- err
				return
			}
		}
	}
}

package websocket

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"sync"

	"github.com/deepgram/gnosis/internal/services/tools"
	"github.com/deepgram/gnosis/internal/services/tools/models"
	"github.com/gorilla/websocket"
	"github.com/rs/zerolog/log"
)

type FunctionCallRequest struct {
	Type           string          `json:"type"`
	FunctionName   string          `json:"function_name"`
	FunctionCallID string          `json:"function_call_id"`
	Input          json.RawMessage `json:"input"`
}

type FunctionCallResponse struct {
	Type           string `json:"type"`
	FunctionCallID string `json:"function_call_id"`
	Output         string `json:"output"`
}

type SettingsConfiguration struct {
	Type  string `json:"type"`
	Audio struct {
		Input struct {
			Encoding   string `json:"encoding"`
			SampleRate int    `json:"sample_rate"`
		} `json:"input"`
		Output struct {
			Encoding   string `json:"encoding"`
			SampleRate int    `json:"sample_rate"`
			Bitrate    int    `json:"bitrate"`
			Container  string `json:"container"`
		} `json:"output"`
	} `json:"audio"`
	Agent struct {
		Listen struct {
			Model string `json:"model"`
		} `json:"listen"`
		Think struct {
			Provider struct {
				Type string `json:"type"`
			} `json:"provider"`
			Model        string                          `json:"model"`
			Instructions string                          `json:"instructions"`
			Functions    []models.DeepgramToolCallConfig `json:"functions"`
		} `json:"think"`
		Speak struct {
			Model string `json:"model"`
		} `json:"speak"`
	} `json:"agent"`
	Context struct {
		Messages []json.RawMessage `json:"messages"`
		Replay   bool              `json:"replay"`
	} `json:"context"`
}

type GenericMessage struct {
	Type string `json:"type"`
}

var (
	upgrader = websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool {
			// TODO: Implement proper origin checking based on configuration
			return true
		},
	}
)

// HandleAgentWebSocket handles the voice agent WebSocket proxy connection
func HandleAgentWebSocket(toolService *tools.Service, w http.ResponseWriter, r *http.Request) {
	// Upgrade client connection to WebSocket
	clientConn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Warn().Err(err).Msg("Failed to upgrade client connection to WebSocket")
		return
	}
	defer clientConn.Close()

	log.Debug().
		Str("remote_addr", r.RemoteAddr).
		Str("user_agent", r.UserAgent()).
		Msg("New WebSocket connection attempt")

	log.Trace().
		Str("remote_addr", r.RemoteAddr).
		Str("protocol", r.Proto).
		Interface("headers", r.Header).
		Msg("WebSocket connection details")

	// Connect to the target WebSocket server
	targetURL := "wss://agent.deepgram.com/agent"
	u, err := url.Parse(targetURL)
	if err != nil {
		log.Warn().Str("url", targetURL).Err(err).Msg("Client provided invalid target URL")
		return
	}

	log.Trace().
		Str("target_url", targetURL).
		Interface("query_params", r.URL.Query()).
		Msg("Preparing to establish target WebSocket connection")

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

	log.Debug().
		Str("remote_addr", r.RemoteAddr).
		Str("target_url", targetURL).
		Msg("Attempting to connect to target WebSocket server")

	log.Trace().
		Str("scheme", u.Scheme).
		Str("host", u.Host).
		Str("path", u.Path).
		Msg("Parsed WebSocket target URL components")

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
		Str("target_url", targetURL).
		Msg("Connected to target WebSocket server")

	log.Debug().
		Str("remote_addr", r.RemoteAddr).
		Msg("Client connection upgraded to WebSocket")

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
	go proxyMessages(toolService, clientConn, serverConn, "Client -> Server", done, errChan)

	// Start goroutine to forward server -> client
	go proxyMessages(toolService, serverConn, clientConn, "Server -> Client", done, errChan)

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

	log.Debug().
		Str("remote_addr", r.RemoteAddr).
		Msg("API key validated for WebSocket connection")
}

// Function call messages are received from the Deepgram agent server
// and forwarded to the client.
// Here, we intercept SOME function calls and respond to Deepgram.
// Other function calls are forwarded to the client.
func handleFunctionCall(_ *tools.Service, msg []byte, src *websocket.Conn, dst *websocket.Conn) error {
	var funcRequest FunctionCallRequest
	if err := json.Unmarshal(msg, &funcRequest); err != nil {
		return err
	}

	log.Debug().
		Str("direction", "Server -> Client").
		Str("type", "function_call").
		Interface("function_call", funcRequest).
		Msg("Processing WebSocket message")

	if funcRequest.FunctionName == "ask_kapa" {
		response := FunctionCallResponse{
			Type:           "FunctionCallResponse",
			FunctionCallID: funcRequest.FunctionCallID,
			Output:         "This is a test response",
		}

		responseBytes, err := json.Marshal(response)
		if err != nil {
			return fmt.Errorf("failed to marshal function response: %w", err)
		}

		// send response back to server
		return handleMessage(responseBytes, src)
	}

	// forward message to the client
	return handleMessage(msg, dst)
}

// Client -> Server
func handleSettingsConfiguration(toolService *tools.Service, msg []byte, dst *websocket.Conn) error {
	var settings SettingsConfiguration
	if err := json.Unmarshal(msg, &settings); err != nil {
		return err
	}

	// inject tools into settings
	settings.Agent.Think.Functions = toolService.GetDeepgramTools()

	log.Debug().
		Str("direction", "Server -> Client").
		Str("type", "settings_configuration").
		Interface("settings", settings).
		Msg("Processing WebSocket message")

	// For now, just forward the settings
	settingsBytes, err := json.Marshal(settings)
	if err != nil {
		return fmt.Errorf("failed to marshal settings: %w", err)
	}
	return handleMessage(settingsBytes, dst)
}

func handleMessage(msg []byte, dst *websocket.Conn) error {
	return dst.WriteMessage(websocket.TextMessage, msg)
}

func proxyMessages(toolService *tools.Service, src, dst *websocket.Conn, direction string, done chan struct{}, errChan chan error) {
	for {
		select {
		case <-done:
			return
		default:
			messageType, msg, err := src.ReadMessage()
			if err != nil {
				if !websocket.IsCloseError(err, websocket.CloseNormalClosure) {
					handleMessageError(direction, err, "Failed to read message")
				}
				errChan <- err
				return
			}

			// Try to determine message type
			var genericMsg GenericMessage
			if err := json.Unmarshal(msg, &genericMsg); err != nil {
				handleMessageError(direction, err, "Failed to parse message type")
				continue
			}

			var handleErr error
			switch genericMsg.Type {
			case "FunctionCallRequest":
				handleErr = handleFunctionCall(toolService, msg, src, dst)
			case "SettingsConfiguration":
				handleErr = handleSettingsConfiguration(toolService, msg, dst)
			default:
				handleErr = handleMessage(msg, dst)
			}

			if handleErr != nil {
				handleMessageError(direction, handleErr, "Failed to handle message")
				errChan <- handleErr
				return
			}

			log.Debug().
				Str("direction", direction).
				Int("message_type", messageType).
				Msg("Forwarding WebSocket message")
		}
	}
}

func handleMessageError(direction string, err error, msg string) {
	log.Error().
		Err(err).
		Str("direction", direction).
		Str("context", msg).
		Msg("WebSocket message handling error")
}

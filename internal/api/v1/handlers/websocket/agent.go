package websocket

import (
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/deepgram/gnosis/internal/services/proxy"
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
func HandleAgentWebSocket(toolsService *tools.Service, agentProxyService *proxy.Service, w http.ResponseWriter, r *http.Request) {
	// Upgrade client connection to WebSocket
	clientConn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Warn().Err(err).Msg("Failed to upgrade client connection to WebSocket")
		return
	}
	defer clientConn.Close()

	// Set the socket URL for the Agent service
	deepgramService := agentProxyService.GetDeepgramService()
	deepgramService.SetSocketURL("wss://agent.deepgram.com")

	// Connect to the server
	if err := agentProxyService.ConnectServer("/agent"); err != nil {
		log.Error().Err(err).Msg("Failed to connect to the server")
		return
	}

	// Start the proxy, overload with processors
	agentProxyService.StartProxy(
		clientConn,
		createFunctionCallProcessor(toolsService),
		createSettingsConfigurationProcessor(toolsService),
	)
}

// Create a closure that captures toolService and returns a MessageProcessor
func createFunctionCallProcessor(_ *tools.Service) proxy.MessageProcessor {
	return func(messageType int, message []byte, srcConn *websocket.Conn) (*[]byte, error) {
		var funcRequest FunctionCallRequest
		if err := json.Unmarshal(message, &funcRequest); err != nil {
			return nil, err
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
				return nil, fmt.Errorf("failed to marshal function response: %w", err)
			}

			// simulate sending a message back to the source
			srcConn.WriteMessage(websocket.TextMessage, responseBytes)

			return nil, nil
		}

		// Forward message to client
		return &message, nil
	}
}

func createSettingsConfigurationProcessor(toolService *tools.Service) proxy.MessageProcessor {
	return func(messageType int, message []byte, srcConn *websocket.Conn) (*[]byte, error) {
		var settings SettingsConfiguration
		if err := json.Unmarshal(message, &settings); err != nil {
			return nil, err
		}

		// inject tools into settings
		settings.Agent.Think.Functions = toolService.GetDeepgramTools()

		settingsBytes, err := json.Marshal(settings)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal settings: %w", err)
		}
		return &settingsBytes, nil
	}
}

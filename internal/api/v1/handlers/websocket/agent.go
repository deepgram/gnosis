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
	"github.com/sashabaranov/go-openai"
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
	socketURL = "wss://agent.deepgram.com"
	upgrader  = websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool {
			/*
				TODO: Implement proper origin checking based on configuration and the
				authenticated client's allowed origins
			*/
			return true
		},
	}
)

// HandleAgentWebSocket handles the voice agent WebSocket proxy connection
func HandleAgentWebSocket(toolsService *tools.Service, agentProxyService *proxy.Service, w http.ResponseWriter, r *http.Request) {
	done := make(chan struct{})
	errChan := make(chan error, 1)

	// Upgrade client connection to WebSocket
	clientConn, err := upgrader.Upgrade(w, r, nil)

	// Error if failed to upgrade client connection to WebSocket
	if err != nil {
		log.Error().Err(err).Msg("Failed to upgrade client connection to WebSocket")
		return
	}

	// Close client connection when function returns
	defer clientConn.Close()

	// Set the socket URL for the Agent service
	log.Info().Str("socket_url", socketURL).Msg("Setting Deepgram socket URL")
	deepgramService := agentProxyService.GetDeepgramService()
	deepgramService.SetSocketURL(socketURL)

	// Connect to the server
	agentProxyService.ConnectServer("/agent", done, errChan)

	log.Info().Msg("Successfully connected to upstream server, starting proxy")

	// Start the proxy with processors
	agentProxyService.StartProxy(
		clientConn,
		createFunctionCallProcessor(toolsService, r),
		createSettingsConfigurationProcessor(toolsService, r),
	)

	// Handle shutdown
	select {
	case err := <-errChan:
		log.Printf("proxy error: %v", err)
		clientConn.Close()
		agentProxyService.Close()
	case <-r.Context().Done():
		clientConn.Close()
		agentProxyService.Close()
		close(done)
	}
}

// Create a closure that captures toolService and returns a MessageProcessor
// MessageProcessor is for running any tool/function calls that are received from the Deepgram server.
// Closure returns true if it was skipped, false if it was processed or errored.
func createFunctionCallProcessor(toolService *tools.Service, r *http.Request) proxy.MessageProcessor {
	return func(messageType int, message []byte, srcConn *websocket.Conn) (bool, *[]byte, error) {
		var funcRequest FunctionCallRequest

		// Unmarshal the message
		if err := json.Unmarshal(message, &funcRequest); err != nil {
			// If the message is not a function call, return true to skip it
			return false, nil, fmt.Errorf("failed to unmarshal function call request: %w", err)
		}

		// If the message is not a function call, return true to skip it
		if funcRequest.Type != "FunctionCallRequest" {
			return true, nil, nil
		}

		log.Debug().
			Str("direction", "Server -> Client").
			Str("type", "function_call").
			Interface("function_call", funcRequest).
			Msg("Processing WebSocket message")

		// Convert to OpenAI tool call format
		toolCall := openai.ToolCall{
			ID:   funcRequest.FunctionCallID,
			Type: "function",
			Function: openai.FunctionCall{
				Name:      funcRequest.FunctionName,
				Arguments: string(funcRequest.Input),
			},
		}

		// Execute the tool call
		result, err := toolService.GetToolExecutor().ExecuteToolCall(r.Context(), toolCall)
		if err != nil {
			return false, nil, fmt.Errorf("failed to execute tool call: %w", err)
		}

		response := FunctionCallResponse{
			Type:           "FunctionCallResponse",
			FunctionCallID: funcRequest.FunctionCallID,
			Output:         result,
		}

		responseBytes, err := json.Marshal(response)
		if err != nil {
			return false, nil, fmt.Errorf("failed to marshal function response: %w", err)
		}

		// Send response back to the source
		srcConn.WriteMessage(websocket.TextMessage, responseBytes)
		return false, &responseBytes, nil
	}
}

// Create a closure that captures toolService and returns a MessageProcessor
// MessageProcessor is for injecting tool configuration into the settings sent to the Deepgram server.
// Closure returns true if it was skipped, false if it was processed or errored.
func createSettingsConfigurationProcessor(toolService *tools.Service, _ *http.Request) proxy.MessageProcessor {
	return func(messageType int, message []byte, srcConn *websocket.Conn) (bool, *[]byte, error) {
		var settings SettingsConfiguration

		// Unmarshal the message
		if err := json.Unmarshal(message, &settings); err != nil {
			// If the message is not a settings configuration, return true to skip it
			return false, nil, fmt.Errorf("failed to unmarshal settings configuration: %w", err)
		}

		// If the message is not a settings configuration, return true to skip it
		if settings.Type != "SettingsConfiguration" {
			return true, nil, nil
		}

		// inject tools into settings
		settings.Agent.Think.Functions = toolService.GetDeepgramTools()

		settingsBytes, err := json.Marshal(settings)
		if err != nil {
			return false, nil, fmt.Errorf("failed to marshal settings: %w", err)
		}
		return false, &settingsBytes, nil
	}
}

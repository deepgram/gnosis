package handlers

import (
	"encoding/json"

	"github.com/deepgram/navi/internal/assistant"
	"github.com/google/uuid"
	"github.com/gorilla/websocket"
)

// HandleAssistantMessage processes incoming messages on the assistant channel
func HandleAssistantMessage(conn *websocket.Conn, messageType int, data []byte) error {
	var msg assistant.UserMessage
	if err := json.Unmarshal(data, &msg); err != nil {
		return sendErrorResponse(conn, "Invalid message format")
	}

	// Generate a unique request ID
	requestID := uuid.New().String()

	// Send initial streaming response
	if err := sendStreamingResponse(conn, requestID, msg.MessageID, "Processing your message..."); err != nil {
		return err
	}

	// TODO: Implement actual assistant logic here
	// For now, just echo back the message as complete
	response := assistant.AssistantResponse{
		RequestID: requestID,
		MessageID: msg.MessageID,
		Content:   msg.Content,
		Status:    assistant.StatusComplete,
	}

	return conn.WriteJSON(response)
}

func sendStreamingResponse(conn *websocket.Conn, requestID, messageID, content string) error {
	response := assistant.AssistantResponse{
		RequestID: requestID,
		MessageID: messageID,
		Content:   content,
		Status:    assistant.StatusStreaming,
	}
	return conn.WriteJSON(response)
}

func sendErrorResponse(conn *websocket.Conn, errMsg string) error {
	response := assistant.AssistantResponse{
		RequestID: uuid.New().String(),
		Content:   errMsg,
		Status:    assistant.StatusError,
	}
	return conn.WriteJSON(response)
}

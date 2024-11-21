package v1

import (
	"encoding/json"
	"net/http"

	"github.com/deepgram/codename-sage/internal/logger"
	"github.com/deepgram/codename-sage/internal/services/chat"
	"github.com/deepgram/codename-sage/internal/services/oauth"
)

type ChatCompletionRequest struct {
	Messages []chat.ChatMessage `json:"messages"`
}

type ChatCompletionResponse struct {
	Messages []chat.ChatMessage `json:"messages"`
}

func HandleChatCompletion(w http.ResponseWriter, r *http.Request) {
	logger.Debug("Starting chat completion handler")
	logger.Info("Received chat completion request")

	tokenString := oauth.ExtractToken(r)
	if tokenString == "" {
		logger.Error("Missing authorization token")
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	logger.Debug("Token extracted, proceeding with validation")
	validation := oauth.ValidateToken(tokenString)
	if !validation.Valid {
		logger.Error("Invalid authorization token: %v", validation)
		http.Error(w, "Invalid token", http.StatusUnauthorized)
		return
	}

	logger.Info("Request authenticated for client type: %s", validation.ClientType)
	logger.Debug("Beginning request body parsing")

	var req ChatCompletionRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error("Failed to decode chat completion request: %v", err)
		http.Error(w, "Invalid request format", http.StatusBadRequest)
		return
	}

	if len(req.Messages) == 0 {
		logger.Error("Request must contain at least one message")
		http.Error(w, "Request must contain at least one message", http.StatusBadRequest)
		return
	}
	logger.Info("Chat completion request received, processing with %d messages", len(req.Messages))

	for _, msg := range req.Messages {
		if msg.Role != "user" && msg.Role != "assistant" {
			logger.Error("Invalid message role: %s", msg.Role)
			http.Error(w, "Message role must be 'user' or 'assistant'", http.StatusBadRequest)
			return
		}
	}

	logger.Debug("Initializing chat service")

	chatService := chat.NewService()
	response, err := chatService.ProcessChat(r.Context(), req.Messages)
	if err != nil {
		logger.Error("Chat service error: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	resp := ChatCompletionResponse{
		Messages: append(req.Messages, *response),
	}

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(resp); err != nil {
		logger.Error("Failed to encode response: %v", err)
		return
	}

	logger.Info("Chat completion response generated successfully")
}

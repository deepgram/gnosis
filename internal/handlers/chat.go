package handlers

import (
	"encoding/json"
	"net/http"

	"github.com/deepgram/codename-sage/internal/logger"
	"github.com/deepgram/codename-sage/internal/services/chat"
	"github.com/sashabaranov/go-openai"
)

type ChatCompletionRequest struct {
	Messages []openai.ChatCompletionMessage `json:"messages"`
}

func HandleChatCompletion(w http.ResponseWriter, r *http.Request) {
	logger.Debug("Starting chat completion handler")
	logger.Info("Received chat completion request")

	tokenString := extractToken(r)
	if tokenString == "" {
		logger.Error("Missing authorization token")
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	logger.Debug("Token extracted, proceeding with validation")
	validation := validateToken(tokenString)
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
		logger.Warn("Received chat completion request with empty messages array")
	}
	logger.Info("Chat completion request validated, processing with %d messages", len(req.Messages))
	logger.Debug("Initializing chat service")

	chatService := chat.NewService()
	response, err := chatService.ProcessChat(r.Context(), req.Messages)
	if err != nil {
		logger.Error("Chat service error: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	logger.Debug("Setting response headers")
	w.Header().Set("Content-Type", "application/json")

	if err := json.NewEncoder(w).Encode(response); err != nil {
		logger.Error("Failed to encode response: %v", err)
		return
	}

	logger.Info("Chat completion response generated successfully")
	logger.Debug("Handler completed successfully")
}

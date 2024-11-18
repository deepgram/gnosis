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
	logger.Info("Received chat completion request")

	tokenString := extractToken(r)
	if tokenString == "" {
		logger.Error("Missing authorization token")
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	validation := validateToken(tokenString)
	if !validation.Valid {
		logger.Error("Invalid authorization token")
		http.Error(w, "Invalid token", http.StatusUnauthorized)
		return
	}

	logger.Info("Request from client type: %s", validation.ClientType)

	var req ChatCompletionRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error("Failed to decode chat completion request: %v", err)
		http.Error(w, "Invalid request format", http.StatusBadRequest)
		return
	}

	logger.Info("Chat completion request validated, processing with %d messages", len(req.Messages))

	chatService := chat.NewService()
	response, err := chatService.ProcessChat(r.Context(), req.Messages)
	if err != nil {
		logger.Error("Chat service error: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)

	logger.Info("Chat completion response generated successfully")
}

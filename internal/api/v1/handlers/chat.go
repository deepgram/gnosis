package handlers

import (
	"encoding/json"
	"net/http"

	"github.com/deepgram/gnosis/internal/domain/chat"
	"github.com/deepgram/gnosis/internal/domain/chat/models"
	"github.com/deepgram/gnosis/internal/services/oauth"
	"github.com/deepgram/gnosis/pkg/logger"
)

// HandleChatCompletionV1 handles chat completion requests
func HandleChatCompletionV1(chatService chat.Service, w http.ResponseWriter, r *http.Request) {
	logger.Debug(logger.HANDLER, "Starting chat completion handler")

	// Auth validation
	tokenString := oauth.ExtractToken(r)
	if tokenString == "" {
		logger.Error(logger.HANDLER, "Missing authorization token")
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	validation := oauth.ValidateToken(tokenString)
	if !validation.Valid {
		logger.Error(logger.HANDLER, "Invalid authorization token: %v", validation)
		http.Error(w, "Invalid token", http.StatusUnauthorized)
		return
	}

	// Parse request
	var req struct {
		Messages []models.ChatMessage `json:"messages"`
		Config   *models.ChatConfig   `json:"config,omitempty"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error(logger.HANDLER, "Failed to decode chat completion request: %v", err)
		http.Error(w, "Invalid request format", http.StatusBadRequest)
		return
	}

	// Validate request
	if len(req.Messages) == 0 {
		logger.Error(logger.HANDLER, "Empty messages array in request")
		http.Error(w, "Messages array cannot be empty", http.StatusBadRequest)
		return
	}

	// Use default config if none provided
	if req.Config == nil {
		req.Config = &models.ChatConfig{
			Temperature:     0.7,
			MaxTokens:       1000,
			TopP:            1.0,
			PresencePenalty: 0.0,
		}
	}

	// Process chat
	resp, err := chatService.ProcessChat(r.Context(), req.Messages, req.Config)
	if err != nil {
		logger.Error(logger.HANDLER, "Failed to process chat: %v", err)
		http.Error(w, "Failed to process chat", http.StatusInternalServerError)
		return
	}

	// Send response
	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(resp); err != nil {
		logger.Error(logger.HANDLER, "Failed to encode response: %v", err)
		http.Error(w, "Failed to encode response", http.StatusInternalServerError)
		return
	}
}

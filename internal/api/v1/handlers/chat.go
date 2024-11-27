package handlers

import (
	"encoding/json"
	"net/http"

	"github.com/deepgram/gnosis/internal/services/chat"
	chatModels "github.com/deepgram/gnosis/internal/services/chat/models"
	"github.com/deepgram/gnosis/internal/services/oauth"
	"github.com/deepgram/gnosis/pkg/httpext"
	"github.com/deepgram/gnosis/pkg/logger"
)

// HandleChatCompletion handles chat completion requests
func HandleChatCompletion(chatService chat.Service, w http.ResponseWriter, r *http.Request) {
	logger.Debug(logger.HANDLER, "Starting chat completion handler")

	// Auth validation
	tokenString := oauth.ExtractToken(r)
	if tokenString == "" {
		logger.Error(logger.HANDLER, "Missing authorization token")
		httpext.JsonError(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	validation := oauth.ValidateToken(tokenString)
	if !validation.Valid {
		logger.Error(logger.HANDLER, "Invalid authorization token: %v", validation)
		httpext.JsonError(w, "Invalid token", http.StatusUnauthorized)
		return
	}

	// Parse request
	var req struct {
		Messages []chatModels.ChatMessage `json:"messages"`
		Config   *chatModels.ChatConfig   `json:"config,omitempty"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error(logger.HANDLER, "Failed to decode chat completion request: %v", err)
		httpext.JsonError(w, "Invalid request format", http.StatusBadRequest)
		return
	}

	// Validate request
	if len(req.Messages) == 0 {
		logger.Error(logger.HANDLER, "Empty messages array in request")
		httpext.JsonError(w, "Messages array cannot be empty", http.StatusBadRequest)
		return
	}

	// Use default config if none provided
	if req.Config == nil {
		req.Config = &chatModels.ChatConfig{
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
		httpext.JsonError(w, "Failed to process chat", http.StatusInternalServerError)
		return
	}

	// Send response
	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(resp); err != nil {
		logger.Error(logger.HANDLER, "Failed to encode response: %v", err)
		httpext.JsonError(w, "Failed to encode response", http.StatusInternalServerError)
		return
	}
}

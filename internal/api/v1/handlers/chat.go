package handlers

import (
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/deepgram/gnosis/internal/services/chat"
	chatModels "github.com/deepgram/gnosis/internal/services/chat/models"
	"github.com/deepgram/gnosis/pkg/httpext"
	"github.com/rs/zerolog/log"
)

// HandleChatCompletion handles chat completion requests
func HandleChatCompletion(chatService chat.Service, w http.ResponseWriter, r *http.Request) {
	// Parse request
	var req struct {
		Messages []chatModels.ChatMessage `json:"messages"`
		Config   *chatModels.ChatConfig   `json:"config,omitempty"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		log.Warn().Err(err).Msg("Client sent malformed JSON request")
		httpext.JsonError(w, "Invalid request format", http.StatusBadRequest)
		return
	}

	// Validate request
	if len(req.Messages) == 0 {
		log.Warn().Msg("Client sent empty messages array")
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
		// log the error and the request
		log.Error().Err(err).Str("messages", fmt.Sprintf("%v", req.Messages)).Str("config", fmt.Sprintf("%v", req.Config)).Msg("Failed to process chat")
		httpext.JsonError(w, "Failed to process chat", http.StatusInternalServerError)
		return
	}

	// Send response
	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(resp); err != nil {
		// log the error and the response
		log.Error().Err(err).Str("response", fmt.Sprintf("%v", resp)).Msg("Failed to encode response")
		httpext.JsonError(w, "Failed to encode response", http.StatusInternalServerError)
		return
	}
}

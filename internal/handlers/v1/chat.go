package v1

import (
	"encoding/json"
	"net/http"

	"github.com/deepgram/gnosis/internal/logger"
	"github.com/deepgram/gnosis/internal/services/chat"
	"github.com/deepgram/gnosis/internal/services/oauth"
)

type ChatCompletionRequest struct {
	Messages         []chat.ChatMessage `json:"messages"`
	Temperature      float32            `json:"temperature,omitempty"`
	MaxTokens        int                `json:"max_tokens,omitempty"`
	TopP             float32            `json:"top_p,omitempty"`
	PresencePenalty  float32            `json:"presence_penalty,omitempty"`
	FrequencyPenalty float32            `json:"frequency_penalty,omitempty"`
}

func HandleChatCompletion(chatService *chat.Service, w http.ResponseWriter, r *http.Request) {
	logger.Debug(logger.HANDLER, "Starting chat completion handler")
	logger.Info(logger.HANDLER, "Received chat completion request")

	tokenString := oauth.ExtractToken(r)
	if tokenString == "" {
		logger.Error(logger.HANDLER, "Missing authorization token")
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	logger.Debug(logger.HANDLER, "Token extracted, proceeding with validation")
	validation := oauth.ValidateToken(tokenString)
	if !validation.Valid {
		logger.Error(logger.HANDLER, "Invalid authorization token: %v", validation)
		http.Error(w, "Invalid token", http.StatusUnauthorized)
		return
	}

	logger.Info(logger.HANDLER, "Request authenticated for client type: %s", validation.ClientType)
	logger.Debug(logger.HANDLER, "Beginning request body parsing")

	var req ChatCompletionRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error(logger.HANDLER, "Failed to decode chat completion request: %v", err)
		http.Error(w, "Invalid request format", http.StatusBadRequest)
		return
	}

	if len(req.Messages) == 0 {
		logger.Error(logger.HANDLER, "Request must contain at least one message")
		http.Error(w, "Request must contain at least one message", http.StatusBadRequest)
		return
	}

	if req.Temperature < 0 || req.Temperature > 2 {
		logger.Error(logger.HANDLER, "Invalid temperature value: %f", req.Temperature)
		http.Error(w, "Temperature must be between 0 and 2", http.StatusBadRequest)
		return
	}

	if req.TopP < 0 || req.TopP > 1 {
		logger.Error(logger.HANDLER, "Invalid top_p value: %f", req.TopP)
		http.Error(w, "Top_p must be between 0 and 1", http.StatusBadRequest)
		return
	}

	if req.MaxTokens < 0 || req.MaxTokens > 4096 {
		logger.Error(logger.HANDLER, "Invalid max_tokens value: %d", req.MaxTokens)
		http.Error(w, "Max_tokens must be between 1 and 4096", http.StatusBadRequest)
		return
	}

	config := &chat.ChatConfig{
		Temperature:      req.Temperature,
		MaxTokens:        req.MaxTokens,
		TopP:             req.TopP,
		PresencePenalty:  req.PresencePenalty,
		FrequencyPenalty: req.FrequencyPenalty,
	}

	response, err := chatService.ProcessChat(r.Context(), req.Messages, config)
	if err != nil {
		logger.Error(logger.HANDLER, "Chat service error: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(response); err != nil {
		logger.Error(logger.HANDLER, "Failed to encode response: %v", err)
		return
	}

	logger.Info(logger.HANDLER, "Chat completion response generated successfully")
}

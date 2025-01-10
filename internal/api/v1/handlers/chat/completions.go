package chat

import (
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/deepgram/gnosis/internal/services/chat"
	"github.com/deepgram/gnosis/internal/services/chat/models"
	"github.com/deepgram/gnosis/pkg/httpext"
	"github.com/go-playground/validator/v10"
	"github.com/rs/zerolog/log"
	"github.com/sashabaranov/go-openai"
)

// HandleChatCompletions handles chat completions requests
// TODO: update chat endpoint to use the latest change to the OpenAPI spec
// Issue URL: https://github.com/deepgram/gnosis/issues/24
func HandleChatCompletions(chatService chat.Service, w http.ResponseWriter, r *http.Request) {
	// Parse request
	var req models.ChatCompletionRequest

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		log.Warn().Err(err).Msg("Client sent malformed JSON request")
		httpext.JsonError(w, "Invalid request format", http.StatusBadRequest)
		return
	}

	// use a single instance of Validate, it caches struct info
	validate := validator.New(validator.WithRequiredStructEnabled())

	// Validate request against model constraints
	if err := validate.Struct(req); err != nil {
		log.Warn().Err(err).Msg("Request validation failed")
		httpext.JsonError(w, fmt.Sprintf("Invalid request: %v", err), http.StatusBadRequest)
		return
	}

	// convert the `req` to the openai request
	// the big difference is that response_format.json_schema.schema is a json.RawMessage
	// and the openai request expects a json.Marshaler
	openaiReq := openai.ChatCompletionRequest{
		Model:               req.Model,
		Messages:            req.Messages,
		MaxTokens:           req.MaxTokens,
		MaxCompletionTokens: req.MaxCompletionTokens,
		Temperature:         req.Temperature,
		TopP:                req.TopP,
		N:                   req.N,
		Stream:              req.Stream,
		Stop:                req.Stop,
		PresencePenalty:     req.PresencePenalty,
		FrequencyPenalty:    req.FrequencyPenalty,
		LogitBias:           req.LogitBias,
		LogProbs:            req.LogProbs,
		TopLogProbs:         req.TopLogProbs,
		User:                req.User,
		Functions:           req.Functions,
		FunctionCall:        req.FunctionCall,
		Tools:               req.Tools,
		ToolChoice:          req.ToolChoice,
		StreamOptions:       req.StreamOptions,
		ParallelToolCalls:   req.ParallelToolCalls,
		Store:               req.Store,
		Metadata:            req.Metadata,
	}

	// Handle response format conversion if present
	if req.ResponseFormat != nil {
		openaiReq.ResponseFormat = &openai.ChatCompletionResponseFormat{
			Type: openai.ChatCompletionResponseFormatType(req.ResponseFormat.Type),
		}
		if req.ResponseFormat.JSONSchema != nil {
			openaiReq.ResponseFormat.JSONSchema = &openai.ChatCompletionResponseFormatJSONSchema{
				Name:        req.ResponseFormat.JSONSchema.Name,
				Description: req.ResponseFormat.JSONSchema.Description,
				Schema:      req.ResponseFormat.JSONSchema.Schema,
				Strict:      req.ResponseFormat.JSONSchema.Strict,
			}
		}
	}

	// trace level log of the JSON request body pretty printed
	if log.Trace().Enabled() {
		prettyJSON, err := json.MarshalIndent(req, "", "    ")
		if err == nil {
			log.Trace().RawJSON("request_body", prettyJSON).Msg("Incoming completions request")
		}
	}

	log.Info().
		Int("message_count", len(req.Messages)).
		Str("client_ip", r.RemoteAddr).
		Msg("Received chat completions request")

	// Validate request
	if len(req.Messages) == 0 {
		log.Warn().Msg("Client sent empty messages array")
		httpext.JsonError(w, "Messages array cannot be empty", http.StatusBadRequest)
		return
	}

	// Process chat
	resp, err := chatService.ProcessChat(r.Context(), openaiReq)
	if err != nil {
		// log the error and the request
		log.Error().Err(err).Str("messages", fmt.Sprintf("%v", req.Messages)).Msg("Failed to process chat")
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

	log.Info().
		Str("client_ip", r.RemoteAddr).
		Int("status", http.StatusOK).
		Msg("Chat completions request processed successfully")
}

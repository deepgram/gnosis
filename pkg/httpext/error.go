package httpext

import (
	"encoding/json"
	"net/http"

	"github.com/deepgram/gnosis/pkg/logger"
)

// ErrorResponse represents a standardised JSON error response
type ErrorResponse struct {
	Error            string `json:"error"`
	ErrorDescription string `json:"error_description,omitempty"`
	ErrorURI         string `json:"error_uri,omitempty"`
}

// JsonError writes a JSON error response with the specified status code
func JsonError(w http.ResponseWriter, message string, code int) {
	response := ErrorResponse{
		Error: message,
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)

	if err := json.NewEncoder(w).Encode(response); err != nil {
		logger.Error(logger.HANDLER, "Failed to encode error response: %v", err)
		// Fallback to writing JSON body as plain text if JSON encoding fails
		http.Error(w, "{\"error\":\"Internal Server Error\"}", http.StatusInternalServerError)
		return
	}
}

// JsonErrorWithDetails writes a detailed JSON error response with optional description and URI
func JsonErrorWithDetails(w http.ResponseWriter, code int, err ErrorResponse) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)

	if err := json.NewEncoder(w).Encode(err); err != nil {
		logger.Error(logger.HANDLER, "Failed to encode detailed error response: %v", err)
		http.Error(w, "{\"error\":\"Internal Server Error\"}", http.StatusInternalServerError)
		return
	}
}

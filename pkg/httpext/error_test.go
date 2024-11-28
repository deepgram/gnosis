package httpext

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestJsonError(t *testing.T) {
	tests := []struct {
		name           string
		message        string
		code           int
		expectedStatus int
		expectedBody   ErrorResponse
	}{
		{
			name:           "Basic error",
			message:        "Something went wrong",
			code:           http.StatusBadRequest,
			expectedStatus: http.StatusBadRequest,
			expectedBody: ErrorResponse{
				Error: "Something went wrong",
			},
		},
		{
			name:           "Internal server error",
			message:        "Internal error",
			code:           http.StatusInternalServerError,
			expectedStatus: http.StatusInternalServerError,
			expectedBody: ErrorResponse{
				Error: "Internal error",
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			w := httptest.NewRecorder()
			JsonError(w, tt.message, tt.code)

			if w.Code != tt.expectedStatus {
				t.Errorf("Expected status code %d, got %d", tt.expectedStatus, w.Code)
			}

			if w.Header().Get("Content-Type") != "application/json" {
				t.Errorf("Expected Content-Type application/json, got %s", w.Header().Get("Content-Type"))
			}

			var response ErrorResponse
			if err := json.NewDecoder(w.Body).Decode(&response); err != nil {
				t.Fatalf("Failed to decode response body: %v", err)
			}

			if response.Error != tt.expectedBody.Error {
				t.Errorf("Expected error message %q, got %q", tt.expectedBody.Error, response.Error)
			}
		})
	}
}

func TestJsonErrorWithDetails(t *testing.T) {
	tests := []struct {
		name           string
		errorResponse  ErrorResponse
		code           int
		expectedStatus int
	}{
		{
			name: "Error with description",
			errorResponse: ErrorResponse{
				Error:            "invalid_request",
				ErrorDescription: "Missing required parameter",
				ErrorURI:         "https://example.com/docs/errors",
			},
			code:           http.StatusBadRequest,
			expectedStatus: http.StatusBadRequest,
		},
		{
			name: "Error without optional fields",
			errorResponse: ErrorResponse{
				Error: "unauthorized",
			},
			code:           http.StatusUnauthorized,
			expectedStatus: http.StatusUnauthorized,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			w := httptest.NewRecorder()
			JsonErrorWithDetails(w, tt.code, tt.errorResponse)

			if w.Code != tt.expectedStatus {
				t.Errorf("Expected status code %d, got %d", tt.expectedStatus, w.Code)
			}

			if w.Header().Get("Content-Type") != "application/json" {
				t.Errorf("Expected Content-Type application/json, got %s", w.Header().Get("Content-Type"))
			}

			var response ErrorResponse
			if err := json.NewDecoder(w.Body).Decode(&response); err != nil {
				t.Fatalf("Failed to decode response body: %v", err)
			}

			if response.Error != tt.errorResponse.Error {
				t.Errorf("Expected error %q, got %q", tt.errorResponse.Error, response.Error)
			}

			if response.ErrorDescription != tt.errorResponse.ErrorDescription {
				t.Errorf("Expected error description %q, got %q", tt.errorResponse.ErrorDescription, response.ErrorDescription)
			}

			if response.ErrorURI != tt.errorResponse.ErrorURI {
				t.Errorf("Expected error URI %q, got %q", tt.errorResponse.ErrorURI, response.ErrorURI)
			}
		})
	}
}

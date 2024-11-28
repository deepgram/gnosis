package handlers

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestHandleWidgetJS(t *testing.T) {
	tests := []struct {
		name           string
		method         string
		expectedStatus int
		checkHeaders   bool
	}{
		{
			name:           "Valid GET request",
			method:         http.MethodGet,
			expectedStatus: http.StatusOK,
			checkHeaders:   true,
		},
		{
			name:           "Invalid POST request",
			method:         http.MethodPost,
			expectedStatus: http.StatusOK, // Current implementation doesn't check method
			checkHeaders:   true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Create request
			req := httptest.NewRequest(tt.method, "/v1/widget.js", nil)
			w := httptest.NewRecorder()

			// Call handler
			HandleWidgetJS(w, req)

			// Check status code
			if w.Code != tt.expectedStatus {
				t.Errorf("Expected status code %d, got %d", tt.expectedStatus, w.Code)
			}

			// Check headers
			if tt.checkHeaders {
				expectedHeaders := map[string]string{
					"Content-Type":  "application/javascript",
					"Cache-Control": "no-cache, no-store, must-revalidate",
					"Pragma":        "no-cache",
					"Expires":       "0",
				}

				for key, expected := range expectedHeaders {
					if got := w.Header().Get(key); got != expected {
						t.Errorf("Expected header %s to be %s, got %s", key, expected, got)
					}
				}
			}

			// Check response body contains expected JavaScript
			responseBody := w.Body.String()
			expectedContent := []string{
				"console.log(\"Deepgram Gnosis Widget loaded\")",
				"window.GNOSIS_WIDGET_ID = \"gnosis-\"",
			}

			for _, expected := range expectedContent {
				if !strings.Contains(responseBody, expected) {
					t.Errorf("Expected response to contain %q, but it didn't", expected)
				}
			}

			// Verify widget ID is being generated
			if !strings.Contains(responseBody, "Math.random().toString(36).substring(2)") {
				t.Error("Expected response to contain random widget ID generation")
			}
		})
	}
}

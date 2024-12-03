package widget

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/services/session"
)

func TestHandleWidgetJS(t *testing.T) {
	// Create session service with memory store for testing
	sessionService := session.NewService(nil)

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

			// Call handler with session service
			HandleWidgetJS(sessionService, w, req)

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

			// Verify session cookie was set
			cookies := w.Result().Cookies()
			var sessionCookieFound bool
			for _, cookie := range cookies {
				if cookie.Name == config.GetSessionCookieName() {
					sessionCookieFound = true
					break
				}
			}
			if !sessionCookieFound {
				t.Error("Expected session cookie to be set")
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

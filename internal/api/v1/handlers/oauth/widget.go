package oauth

import (
	"encoding/json"
	"net/http"
	"strings"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/services/oauth"
	"github.com/deepgram/gnosis/internal/services/widgetcode"
	"github.com/deepgram/gnosis/pkg/httpext"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/rs/zerolog/log"
)

type WidgetAuthRequest struct {
	ClientID string `json:"client_id"`
	State    string `json:"state"`
}

type WidgetAuthResponse struct {
	Code  string `json:"code"`
	State string `json:"state"`
}

type WidgetCodeRequest struct {
	GrantType string `json:"grant_type"`
	ClientID  string `json:"client_id"`
	Code      string `json:"code"`
}

// HandleWidgetAuth handles the widget auth request
// TODO: modify to act as a /oauth/token endpoint that checks for a cookie and
// a client ID, and issues a access token with a refresh token, instead of acting
// as an /oauth/authorize endpoint
func HandleWidgetAuth(widgetCodeService *widgetcode.Service, w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		log.Warn().
			Str("method", r.Method).
			Str("path", r.URL.Path).
			Msg("Invalid HTTP method for widget auth endpoint")
		httpext.JsonError(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Validate session cookie
	cookie, err := r.Cookie(config.GetSessionCookieName())
	if err != nil {
		log.Warn().
			Err(err).
			Str("path", r.URL.Path).
			Msg("Widget auth attempted without valid session cookie")
		httpext.JsonError(w, "Unauthorized - Invalid session cookie", http.StatusUnauthorized)
		return
	}

	// Validate JWT in cookie
	token, err := jwt.ParseWithClaims(cookie.Value, &oauth.CustomClaims{}, func(token *jwt.Token) (interface{}, error) {
		return config.GetJWTSecret(), nil
	})
	if err != nil || !token.Valid {
		httpext.JsonError(w, "Unauthorized - Invalid session cookie", http.StatusUnauthorized)
		return
	}

	// Parse request body
	var req WidgetAuthRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		log.Warn().
			Err(err).
			Msg("Malformed widget auth request received")
		httpext.JsonError(w, "Invalid request format", http.StatusBadRequest)
		return
	}

	// Validate required parameters
	if req.ClientID == "" || req.State == "" {
		httpext.JsonError(w, "Missing required parameters", http.StatusBadRequest)
		return
	}

	// Validate client ID
	clientType := config.GetClientTypeByID(req.ClientID)
	if clientType == "" {
		httpext.JsonError(w, "Invalid client credentials", http.StatusUnauthorized)
		return
	}

	// In HandleAuthorize after validating client ID
	if clientType == "widget" {
		client := config.GetClientConfig(clientType)
		if !validateWidgetRequest(r, client.AllowedURLs) {
			httpext.JsonError(w, "Invalid request origin", http.StatusForbidden)
			return
		}
	}

	// Generate widget code
	widgetCode := uuid.New().String()

	// Store the widget code using the service
	ctx := r.Context()
	if err := widgetCodeService.StoreWidgetCode(ctx, widgetCode, req.ClientID, req.State); err != nil {
		httpext.JsonError(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	response := WidgetAuthResponse{
		Code:  widgetCode,
		State: req.State,
	}

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(response); err != nil {
		log.Printf("Failed to encode response: %v", err)
		return
	}
}

func validateWidgetRequest(r *http.Request, allowedURLs []string) bool {
	origin := r.Header.Get("Origin")
	referer := r.Header.Get("Referer")

	if origin == "" && referer == "" {
		return false
	}

	// Validate origin if present
	if origin != "" {
		originValid := false
		for _, allowed := range allowedURLs {
			if strings.HasPrefix(origin, allowed) {
				originValid = true
				break
			}
		}

		if !originValid {
			return false
		}
	}

	// Validate referer if present
	if referer != "" {
		refererValid := false
		for _, allowed := range allowedURLs {
			if strings.HasPrefix(referer, allowed) {
				refererValid = true
				break
			}
		}

		if !refererValid {
			return false
		}
	}

	// At this point, we have validated at least one of origin or referer
	return true
}

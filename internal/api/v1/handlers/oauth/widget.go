package oauth

import (
	"encoding/json"
	"net/http"
	"strings"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/services/oauth"
	"github.com/deepgram/gnosis/internal/services/widgetcode"
	"github.com/deepgram/gnosis/pkg/httpext"
	"github.com/deepgram/gnosis/pkg/logger"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

func init() {
	logger.Info(logger.HANDLER, "Validating OAuth widget handler configuration")
	// Validate required client configurations
	for clientType, client := range config.AllowedClients {
		if client.ID == "" {
			logger.Error(logger.HANDLER, "Missing required client ID for client: %s", clientType)
		}

		if !client.NoSecret && client.Secret == "" {
			logger.Error(logger.HANDLER, "Missing required secret for client: %s", clientType)
		}

		if clientType == "widget" && len(client.AllowedURLs) == 0 {
			logger.Error(logger.HANDLER, "Missing required allowed URLs for widget client")
		}
	}
	logger.Debug(logger.HANDLER, "OAuth handler initialization complete")
}

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

func HandleWidgetAuth(widgetCodeService *widgetcode.Service, w http.ResponseWriter, r *http.Request) {
	logger.Debug(logger.HANDLER, "Handling widget auth request from %s", r.RemoteAddr)

	if r.Method != http.MethodPost {
		logger.Warn(logger.HANDLER, "Invalid HTTP method %s from %s", r.Method, r.RemoteAddr)
		httpext.JsonError(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Validate session cookie
	cookie, err := r.Cookie(config.GetSessionCookieName())
	if err != nil {
		logger.Warn(logger.HANDLER, "Missing session cookie from %s", r.RemoteAddr)
		httpext.JsonError(w, "Unauthorized - Invalid session cookie", http.StatusUnauthorized)
		return
	}

	// Validate JWT in cookie
	token, err := jwt.ParseWithClaims(cookie.Value, &oauth.CustomClaims{}, func(token *jwt.Token) (interface{}, error) {
		return config.GetJWTSecret(), nil
	})
	if err != nil || !token.Valid {
		logger.Warn(logger.HANDLER, "Invalid session token from %s", r.RemoteAddr)
		httpext.JsonError(w, "Unauthorized - Invalid session cookie", http.StatusUnauthorized)
		return
	}

	// Parse request body
	var req WidgetAuthRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error(logger.HANDLER, "Failed to decode widget auth request: %v", err)
		httpext.JsonError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Validate required parameters
	if req.ClientID == "" || req.State == "" {
		logger.Warn(logger.HANDLER, "Missing required parameters from %s", r.RemoteAddr)
		httpext.JsonError(w, "Missing required parameters", http.StatusBadRequest)
		return
	}

	// Validate client ID
	clientType := config.GetClientTypeByID(req.ClientID)
	if clientType == "" {
		logger.Warn(logger.HANDLER, "Invalid client ID attempted access: %s from %s", req.ClientID, r.RemoteAddr)
		httpext.JsonError(w, "Invalid client credentials", http.StatusUnauthorized)
		return
	}

	// In HandleAuthorize after validating client ID
	if clientType == "widget" {
		client := config.GetClientConfig(clientType)
		if !validateWidgetRequest(r, client.AllowedURLs) {
			logger.Warn(logger.HANDLER, "Invalid widget request origin/referer from %s", r.RemoteAddr)
			httpext.JsonError(w, "Invalid request origin", http.StatusForbidden)
			return
		}
	}

	// Generate widget code
	widgetCode := uuid.New().String()

	// Store the widget code using the service
	ctx := r.Context()
	if err := widgetCodeService.StoreWidgetCode(ctx, widgetCode, req.ClientID, req.State); err != nil {
		logger.Error(logger.HANDLER, "Failed to store widget code: %v", err)
		httpext.JsonError(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	response := WidgetAuthResponse{
		Code:  widgetCode,
		State: req.State,
	}

	logger.Info(logger.HANDLER, "Successfully issued widget code to client ID: %s", req.ClientID)

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(response); err != nil {
		logger.Error(logger.HANDLER, "Failed to encode response: %v", err)
		return
	}
}

func validateWidgetRequest(r *http.Request, allowedURLs []string) bool {
	origin := r.Header.Get("Origin")
	referer := r.Header.Get("Referer")

	logger.Debug(logger.HANDLER, "Validating widget request - Origin: %s, Referer: %s", origin, referer)

	if origin == "" && referer == "" {
		logger.Warn(logger.HANDLER, "Widget request missing both Origin and Referer headers from %s", r.RemoteAddr)
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
			logger.Warn(logger.HANDLER, "Origin not in allowed URLs: %s", origin)
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
			logger.Warn(logger.HANDLER, "Referer not in allowed URLs: %s", referer)
			return false
		}
	}

	// At this point, we have validated at least one of origin or referer
	logger.Debug(logger.HANDLER, "Widget request validation result: %v", true)
	return true
}

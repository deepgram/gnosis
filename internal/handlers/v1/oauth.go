package v1

import (
	"crypto/subtle"
	"encoding/json"
	"net/http"
	"strings"
	"time"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/logger"
	"github.com/deepgram/gnosis/internal/services/oauth"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

var (
	jwtLifetime = 15 * time.Minute
)

func init() {
	logger.Info(logger.HANDLER, "Initializing OAuth handler")
	// Validate required client configurations
	for clientType, client := range config.AllowedClients {
		if client.ID == "" {
			logger.Error("Missing required client ID for client: %s", clientType)
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

type TokenResponse struct {
	AccessToken string `json:"access_token"`
	TokenType   string `json:"token_type"`
	ExpiresIn   int    `json:"expires_in"`
}

type TokenRequest struct {
	GrantType string `json:"grant_type"`
}

func HandleToken(w http.ResponseWriter, r *http.Request) {
	logger.Debug(logger.HANDLER, "Handling token request from %s", r.RemoteAddr)
	if r.Method != http.MethodPost {
		logger.Warn(logger.HANDLER, "Invalid HTTP method %s from %s", r.Method, r.RemoteAddr)
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Log all request headers
	logger.Debug(logger.HANDLER, "Request headers:")
	for name, values := range r.Header {
		for _, value := range values {
			logger.Debug("  %s: %s", name, value)
		}
	}

	// Add client validation before processing the token request
	clientID := r.Header.Get("X-Client-ID")
	clientSecret := r.Header.Get("X-Client-Secret")

	// Log authentication-related headers
	logger.Info(logger.HANDLER, "Authentication details:")
	logger.Info(logger.HANDLER, "  Client ID: %s", clientID)
	logger.Info(logger.HANDLER, "  Client Secret: %s", clientSecret)
	logger.Info(logger.HANDLER, "  Referer: %s", r.Referer())
	logger.Info(logger.HANDLER, "  Origin: %s", r.Header.Get("Origin"))

	// Find the client config by matching ID value
	clientType := config.GetClientTypeByID(clientID)
	client := config.GetClientConfig(clientType)

	logger.Debug(logger.HANDLER, "Identified client type: %s", clientType)

	if clientType == "" {
		logger.Warn(logger.HANDLER, "Invalid client ID attempted access: %s from %s", clientID, r.RemoteAddr)
		http.Error(w, "Invalid client credentials", http.StatusUnauthorized)
		return
	}

	// For widget.js requests, validate origin and referrer before proceeding
	if clientType == "widget" {
		logger.Debug("Validating widget request from origin: %s", r.Header.Get("Origin"))
		if !validateWidgetRequest(r, client.AllowedURLs) {
			logger.Warn(logger.HANDLER, "Invalid widget request origin from %s", r.RemoteAddr)
			http.Error(w, "Invalid request headers", http.StatusForbidden)
			return
		}
		logger.Debug(logger.HANDLER, "Widget request validation successful")
	}

	// Only validate client secret for clients that require it
	if !client.NoSecret {
		logger.Debug("Validating client secret for client type: %s", clientType)
		if !validateClientSecret(clientSecret, client.Secret) {
			logger.Warn(logger.HANDLER, "Invalid client secret attempt for client ID: %s from %s", clientID, r.RemoteAddr)
			http.Error(w, "Invalid client credentials", http.StatusUnauthorized)
			return
		}
		logger.Debug(logger.HANDLER, "Client secret validation successful")
	}

	var req TokenRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error(logger.HANDLER, "Failed to decode token request: %v", err)
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	logger.Info(logger.HANDLER, "Processing token request with grant type: %s", req.GrantType)

	if req.GrantType != config.GrantTypeAnonymous {
		http.Error(w, "Invalid grant type", http.StatusBadRequest)
		return
	}

	// Create custom claims with client type
	claims := oauth.CustomClaims{
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(jwtLifetime)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			ID:        uuid.New().String(),
		},
		ClientType: clientType,
	}

	// Generate JWT with custom claims
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)

	logger.Info(logger.HANDLER, "Generating JWT token for client type: %s", clientType)
	tokenString, err := token.SignedString(config.GetJWTSecret())
	if err != nil {
		logger.Error(logger.HANDLER, "JWT signing failed: %v", err)
		http.Error(w, "Error creating token", http.StatusInternalServerError)
		return
	}

	logger.Info(logger.HANDLER, "Successfully issued token to client ID: %s", clientID)
	logger.Debug(logger.HANDLER, "Token expiry set to: %v", claims.ExpiresAt)

	response := TokenResponse{
		AccessToken: tokenString,
		TokenType:   "Bearer",
		ExpiresIn:   int(jwtLifetime.Seconds()),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func validateClientSecret(provided, stored string) bool {
	return subtle.ConstantTimeCompare([]byte(provided), []byte(stored)) == 1
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

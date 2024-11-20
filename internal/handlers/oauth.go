package handlers

import (
	"crypto/subtle"
	"encoding/json"
	"net/http"
	"strings"
	"time"

	"github.com/deepgram/codename-sage/internal/config"
	"github.com/deepgram/codename-sage/internal/logger"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

var (
	jwtLifetime = 15 * time.Minute
)

func init() {
	logger.Info("Initializing OAuth handler")
	// Validate required client configurations
	for clientType, client := range config.AllowedClients {
		if client.ID == "" {
			logger.Error("Missing required client ID for client: %s", clientType)
		}

		if !client.NoSecret && client.Secret == "" {
			logger.Error("Missing required secret for client: %s", clientType)
		}

		if clientType == "widget" && len(client.AllowedURLs) == 0 {
			logger.Error("Missing required allowed URLs for widget client")
		}
	}
	logger.Debug("OAuth handler initialization complete")
}

type TokenResponse struct {
	AccessToken string `json:"access_token"`
	TokenType   string `json:"token_type"`
	ExpiresIn   int    `json:"expires_in"`
}

type TokenRequest struct {
	GrantType string `json:"grant_type"`
}

type CustomClaims struct {
	jwt.RegisteredClaims
	ClientType string `json:"ctp"`
}

func HandleToken(w http.ResponseWriter, r *http.Request) {
	logger.Debug("Handling token request from %s", r.RemoteAddr)
	if r.Method != http.MethodPost {
		logger.Warn("Invalid HTTP method %s from %s", r.Method, r.RemoteAddr)
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Log all request headers
	logger.Debug("Request headers:")
	for name, values := range r.Header {
		for _, value := range values {
			logger.Debug("  %s: %s", name, value)
		}
	}

	// Add client validation before processing the token request
	clientID := r.Header.Get("X-Client-ID")
	clientSecret := r.Header.Get("X-Client-Secret")

	// Log authentication-related headers
	logger.Info("Authentication details:")
	logger.Info("  Client ID: %s", clientID)
	logger.Info("  Client Secret: %s", clientSecret)
	logger.Info("  Referer: %s", r.Referer())
	logger.Info("  Origin: %s", r.Header.Get("Origin"))

	// Find the client config by matching ID value
	clientType := config.GetClientTypeByID(clientID)
	client := config.GetClientConfig(clientType)

	logger.Debug("Identified client type: %s", clientType)

	if clientType == "" {
		logger.Warn("Invalid client ID attempted access: %s from %s", clientID, r.RemoteAddr)
		http.Error(w, "Invalid client credentials", http.StatusUnauthorized)
		return
	}

	// For widget.js requests, validate origin and referrer before proceeding
	if clientType == "widget" {
		logger.Debug("Validating widget request from origin: %s", r.Header.Get("Origin"))
		if !validateWidgetRequest(r, client.AllowedURLs) {
			logger.Warn("Invalid widget request origin from %s", r.RemoteAddr)
			http.Error(w, "Invalid request headers", http.StatusForbidden)
			return
		}
		logger.Debug("Widget request validation successful")
	}

	// Only validate client secret for clients that require it
	if !client.NoSecret {
		logger.Debug("Validating client secret for client type: %s", clientType)
		if !validateClientSecret(clientSecret, client.Secret) {
			logger.Warn("Invalid client secret attempt for client ID: %s from %s", clientID, r.RemoteAddr)
			http.Error(w, "Invalid client credentials", http.StatusUnauthorized)
			return
		}
		logger.Debug("Client secret validation successful")
	}

	var req TokenRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error("Failed to decode token request: %v", err)
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	logger.Info("Processing token request with grant type: %s", req.GrantType)

	if req.GrantType != config.GrantTypeAnonymous {
		http.Error(w, "Invalid grant type", http.StatusBadRequest)
		return
	}

	// Create custom claims with client type
	claims := CustomClaims{
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(jwtLifetime)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			ID:        uuid.New().String(),
		},
		ClientType: clientType,
	}

	// Generate JWT with custom claims
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)

	logger.Info("Generating JWT token for client type: %s", clientType)
	tokenString, err := token.SignedString(config.GetJWTSecret())
	if err != nil {
		logger.Error("JWT signing failed: %v", err)
		http.Error(w, "Error creating token", http.StatusInternalServerError)
		return
	}

	logger.Info("Successfully issued token to client ID: %s", clientID)
	logger.Debug("Token expiry set to: %v", claims.ExpiresAt)

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

	logger.Debug("Validating widget request - Origin: %s, Referer: %s", origin, referer)

	if origin == "" && referer == "" {
		logger.Warn("Widget request missing both Origin and Referer headers from %s", r.RemoteAddr)
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
			logger.Warn("Origin not in allowed URLs: %s", origin)
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
			logger.Warn("Referer not in allowed URLs: %s", referer)
			return false
		}
	}

	// At this point, we have validated at least one of origin or referer
	logger.Debug("Widget request validation result: %v", true)
	return true
}

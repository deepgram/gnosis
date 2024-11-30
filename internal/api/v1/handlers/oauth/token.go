package oauth

import (
	"bytes"
	"crypto/subtle"
	"encoding/json"
	"io"
	"net/http"
	"time"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/services/oauth"
	"github.com/deepgram/gnosis/internal/services/widgetcode"
	"github.com/deepgram/gnosis/pkg/httpext"
	"github.com/deepgram/gnosis/pkg/logger"
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

type TokenResponse struct {
	AccessToken string `json:"access_token"`
	TokenType   string `json:"token_type"`
	ExpiresIn   int    `json:"expires_in"`
}

type TokenRequest struct {
	GrantType string `json:"grant_type"`
}

type ClientCredentialsRequest struct {
	GrantType    string `json:"grant_type"`
	ClientID     string `json:"client_id"`
	ClientSecret string `json:"client_secret"`
}

func HandleToken(widgetCodeService *widgetcode.Service, w http.ResponseWriter, r *http.Request) {
	logger.Debug(logger.HANDLER, "Handling token request from %s", r.RemoteAddr)
	if r.Method != http.MethodPost {
		logger.Warn(logger.HANDLER, "Invalid HTTP method %s from %s", r.Method, r.RemoteAddr)
		httpext.JsonError(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Read body bytes for reuse
	bodyBytes, err := io.ReadAll(r.Body)
	if err != nil {
		logger.Error(logger.HANDLER, "Failed to read request body: %v", err)
		httpext.JsonError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// First decode to get grant type
	var grantTypeReq struct {
		GrantType string `json:"grant_type"`
	}
	if err := json.NewDecoder(bytes.NewReader(bodyBytes)).Decode(&grantTypeReq); err != nil {
		logger.Error(logger.HANDLER, "Failed to decode grant type: %v", err)
		httpext.JsonError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Reset request body for subsequent reads
	r.Body.Close()
	r.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))

	switch grantTypeReq.GrantType {
	case "client_credentials":
		handleClientCredentials(w, r)
	case "widget":
		handleWidgetCode(widgetCodeService, w, r)
	default:
		logger.Warn(logger.HANDLER, "Invalid grant type: %s", grantTypeReq.GrantType)
		httpext.JsonError(w, "Invalid grant type", http.StatusBadRequest)
		return
	}
}

func handleClientCredentials(w http.ResponseWriter, r *http.Request) {
	var req ClientCredentialsRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error(logger.HANDLER, "Failed to decode client credentials request: %v", err)
		httpext.JsonError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Validate client credentials
	clientType := config.GetClientTypeByID(req.ClientID)
	client := config.GetClientConfig(clientType)

	if clientType == "" || !validateClientSecret(req.ClientSecret, client.Secret) {
		logger.Warn(logger.HANDLER, "Invalid client credentials attempt from %s", r.RemoteAddr)
		httpext.JsonError(w, "Invalid client credentials", http.StatusUnauthorized)
		return
	}

	// Generate JWT token
	claims := oauth.CustomClaims{
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(jwtLifetime)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			ID:        uuid.New().String(),
		},
		ClientType: clientType,
		GrantType:  "client_credentials",
	}

	issueToken(w, claims)
}

func handleWidgetCode(widgetCodeService *widgetcode.Service, w http.ResponseWriter, r *http.Request) {
	var req WidgetCodeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error(logger.HANDLER, "Failed to decode widget code request: %v", err)
		httpext.JsonError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Validate client ID
	clientType := config.GetClientTypeByID(req.ClientID)
	if clientType == "" {
		logger.Warn(logger.HANDLER, "Invalid client ID in auth code request: %s", req.ClientID)
		httpext.JsonError(w, "Invalid client credentials", http.StatusUnauthorized)
		return
	}

	// Validate widget code
	ctx := r.Context()
	authInfo, err := widgetCodeService.ValidateWidgetCode(ctx, req.Code)
	if err != nil || authInfo == nil {
		logger.Warn(logger.HANDLER, "Invalid widget code: %v", err)
		httpext.JsonError(w, "Invalid widget code", http.StatusUnauthorized)
		return
	}

	// Verify the client ID matches the one stored with the auth code
	if authInfo.ClientID != req.ClientID {
		logger.Warn(logger.HANDLER, "Client ID mismatch in widget code request")
		httpext.JsonError(w, "Invalid client credentials", http.StatusUnauthorized)
		return
	}

	// Invalidate the used widget code
	if err := widgetCodeService.InvalidateWidgetCode(ctx, req.Code); err != nil {
		logger.Error(logger.HANDLER, "Failed to invalidate widget code: %v", err)
	}

	// Generate JWT token
	claims := oauth.CustomClaims{
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(jwtLifetime)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			ID:        uuid.New().String(),
		},
		ClientType: clientType,
		GrantType:  "widget",
	}

	issueToken(w, claims)
}

func issueToken(w http.ResponseWriter, claims oauth.CustomClaims) {
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)

	tokenString, err := token.SignedString(config.GetJWTSecret())
	if err != nil {
		logger.Error(logger.HANDLER, "JWT signing failed: %v", err)
		httpext.JsonError(w, "Error creating token", http.StatusInternalServerError)
		return
	}

	response := TokenResponse{
		AccessToken: tokenString,
		TokenType:   "Bearer",
		ExpiresIn:   int(jwtLifetime.Seconds()),
	}

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(response); err != nil {
		logger.Error(logger.HANDLER, "Failed to encode response: %v", err)
		return
	}
}

func validateClientSecret(provided, stored string) bool {
	return subtle.ConstantTimeCompare([]byte(provided), []byte(stored)) == 1
}

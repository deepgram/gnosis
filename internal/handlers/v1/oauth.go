package v1

import (
	"bytes"
	"crypto/subtle"
	"encoding/json"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/logger"
	"github.com/deepgram/gnosis/internal/services/authcode"
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

type AuthorizeRequest struct {
	ClientID string `json:"client_id"`
	State    string `json:"state"`
}

type AuthorizeResponse struct {
	Code  string `json:"code"`
	State string `json:"state"`
}

type ClientCredentialsRequest struct {
	GrantType    string `json:"grant_type"`
	ClientID     string `json:"client_id"`
	ClientSecret string `json:"client_secret"`
}

type AuthorizationCodeRequest struct {
	GrantType string `json:"grant_type"`
	ClientID  string `json:"client_id"`
	Code      string `json:"code"`
}

func HandleToken(authCodeService *authcode.Service, w http.ResponseWriter, r *http.Request) {
	logger.Debug(logger.HANDLER, "Handling token request from %s", r.RemoteAddr)
	if r.Method != http.MethodPost {
		logger.Warn(logger.HANDLER, "Invalid HTTP method %s from %s", r.Method, r.RemoteAddr)
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Read body bytes for reuse
	bodyBytes, err := io.ReadAll(r.Body)
	if err != nil {
		logger.Error(logger.HANDLER, "Failed to read request body: %v", err)
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// First decode to get grant type
	var grantTypeReq struct {
		GrantType string `json:"grant_type"`
	}
	if err := json.NewDecoder(bytes.NewReader(bodyBytes)).Decode(&grantTypeReq); err != nil {
		logger.Error(logger.HANDLER, "Failed to decode grant type: %v", err)
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Reset request body for subsequent reads
	r.Body.Close()
	r.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))

	switch grantTypeReq.GrantType {
	case "client_credentials":
		handleClientCredentials(w, r)
	case "authorization_code":
		handleAuthorizationCode(authCodeService, w, r)
	default:
		logger.Warn(logger.HANDLER, "Invalid grant type: %s", grantTypeReq.GrantType)
		http.Error(w, "Invalid grant type", http.StatusBadRequest)
		return
	}
}

func handleClientCredentials(w http.ResponseWriter, r *http.Request) {
	var req ClientCredentialsRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error(logger.HANDLER, "Failed to decode client credentials request: %v", err)
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Validate client credentials
	clientType := config.GetClientTypeByID(req.ClientID)
	client := config.GetClientConfig(clientType)

	if clientType == "" || !validateClientSecret(req.ClientSecret, client.Secret) {
		logger.Warn(logger.HANDLER, "Invalid client credentials attempt from %s", r.RemoteAddr)
		http.Error(w, "Invalid client credentials", http.StatusUnauthorized)
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
	}

	issueToken(w, claims)
}

func handleAuthorizationCode(authCodeService *authcode.Service, w http.ResponseWriter, r *http.Request) {
	var req AuthorizationCodeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error(logger.HANDLER, "Failed to decode authorization code request: %v", err)
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Validate client ID
	clientType := config.GetClientTypeByID(req.ClientID)
	if clientType == "" {
		logger.Warn(logger.HANDLER, "Invalid client ID in auth code request: %s", req.ClientID)
		http.Error(w, "Invalid client credentials", http.StatusUnauthorized)
		return
	}

	// Validate authorization code
	ctx := r.Context()
	authInfo, err := authCodeService.ValidateAuthCode(ctx, req.Code)
	if err != nil || authInfo == nil {
		logger.Warn(logger.HANDLER, "Invalid authorization code: %v", err)
		http.Error(w, "Invalid authorization code", http.StatusUnauthorized)
		return
	}

	// Verify the client ID matches the one stored with the auth code
	if authInfo.ClientID != req.ClientID {
		logger.Warn(logger.HANDLER, "Client ID mismatch in auth code request")
		http.Error(w, "Invalid client credentials", http.StatusUnauthorized)
		return
	}

	// Invalidate the used authorization code
	if err := authCodeService.InvalidateAuthCode(ctx, req.Code); err != nil {
		logger.Error(logger.HANDLER, "Failed to invalidate auth code: %v", err)
	}

	// Generate JWT token
	claims := oauth.CustomClaims{
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(jwtLifetime)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			ID:        uuid.New().String(),
		},
		ClientType: clientType,
	}

	issueToken(w, claims)
}

func issueToken(w http.ResponseWriter, claims oauth.CustomClaims) {
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)

	tokenString, err := token.SignedString(config.GetJWTSecret())
	if err != nil {
		logger.Error(logger.HANDLER, "JWT signing failed: %v", err)
		http.Error(w, "Error creating token", http.StatusInternalServerError)
		return
	}

	response := TokenResponse{
		AccessToken: tokenString,
		TokenType:   "Bearer",
		ExpiresIn:   int(jwtLifetime.Seconds()),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func HandleAuthorize(authCodeService *authcode.Service, w http.ResponseWriter, r *http.Request) {
	logger.Debug(logger.HANDLER, "Handling authorize request from %s", r.RemoteAddr)

	if r.Method != http.MethodPost {
		logger.Warn(logger.HANDLER, "Invalid HTTP method %s from %s", r.Method, r.RemoteAddr)
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Validate session cookie
	cookie, err := r.Cookie(config.GetSessionCookieName())
	if err != nil {
		logger.Warn(logger.HANDLER, "Missing session cookie from %s", r.RemoteAddr)
		http.Error(w, "Unauthorized - Invalid session cookie", http.StatusUnauthorized)
		return
	}

	// Validate JWT in cookie
	token, err := jwt.ParseWithClaims(cookie.Value, &oauth.CustomClaims{}, func(token *jwt.Token) (interface{}, error) {
		return config.GetJWTSecret(), nil
	})
	if err != nil || !token.Valid {
		logger.Warn(logger.HANDLER, "Invalid session token from %s", r.RemoteAddr)
		http.Error(w, "Unauthorized - Invalid session cookie", http.StatusUnauthorized)
		return
	}

	// Parse request body
	var req AuthorizeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error(logger.HANDLER, "Failed to decode authorize request: %v", err)
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Validate required parameters
	if req.ClientID == "" || req.State == "" {
		logger.Warn(logger.HANDLER, "Missing required parameters from %s", r.RemoteAddr)
		http.Error(w, "Missing required parameters", http.StatusBadRequest)
		return
	}

	// Validate client ID
	clientType := config.GetClientTypeByID(req.ClientID)
	if clientType == "" {
		logger.Warn(logger.HANDLER, "Invalid client ID attempted access: %s from %s", req.ClientID, r.RemoteAddr)
		http.Error(w, "Invalid client credentials", http.StatusUnauthorized)
		return
	}

	// In HandleAuthorize after validating client ID
	if clientType == "widget" {
		client := config.GetClientConfig(clientType)
		if !validateWidgetRequest(r, client.AllowedURLs) {
			logger.Warn(logger.HANDLER, "Invalid widget request origin/referer from %s", r.RemoteAddr)
			http.Error(w, "Invalid request origin", http.StatusForbidden)
			return
		}
	}

	// Generate authorization code
	authCode := uuid.New().String()

	// Store the authorization code using the service
	ctx := r.Context()
	if err := authCodeService.StoreAuthCode(ctx, authCode, req.ClientID, req.State); err != nil {
		logger.Error(logger.HANDLER, "Failed to store auth code: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	response := AuthorizeResponse{
		Code:  authCode,
		State: req.State,
	}

	logger.Info(logger.HANDLER, "Successfully issued authorization code to client ID: %s", req.ClientID)

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

// AuthCodeInfo stores information about an authorization code
type AuthCodeInfo struct {
	ClientID  string
	State     string
	ExpiresAt time.Time
}

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
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/rs/zerolog/log"
)

var (
	jwtLifetime = 15 * time.Minute
)

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

// TODO: modify to support a refresh grant type
func HandleToken(widgetCodeService *widgetcode.Service, w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		httpext.JsonError(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Read body bytes for reuse
	bodyBytes, err := io.ReadAll(r.Body)
	if err != nil {
		httpext.JsonError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// First decode to get grant type
	var grantTypeReq struct {
		GrantType string `json:"grant_type"`
	}
	if err := json.NewDecoder(bytes.NewReader(bodyBytes)).Decode(&grantTypeReq); err != nil {
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
		httpext.JsonError(w, "Invalid grant type", http.StatusBadRequest)
		return
	}
}

func handleClientCredentials(w http.ResponseWriter, r *http.Request) {
	var req ClientCredentialsRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		httpext.JsonError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Validate client credentials
	clientType := config.GetClientTypeByID(req.ClientID)
	client := config.GetClientConfig(clientType)

	if clientType == "" || !validateClientSecret(req.ClientSecret, client.Secret) {
		httpext.JsonError(w, "Invalid client credentials", http.StatusUnauthorized)
		return
	}

	// Generate JWT token with scopes
	claims := oauth.CustomClaims{
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(jwtLifetime)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			ID:        uuid.New().String(),
		},
		ClientType: clientType,
		GrantType:  "client_credentials",
		Scopes:     client.Scopes,
	}

	issueToken(w, claims)
}

func handleWidgetCode(widgetCodeService *widgetcode.Service, w http.ResponseWriter, r *http.Request) {
	var req WidgetCodeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		httpext.JsonError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Validate client ID
	clientType := config.GetClientTypeByID(req.ClientID)
	if clientType == "" {
		httpext.JsonError(w, "Invalid client credentials", http.StatusUnauthorized)
		return
	}

	// Validate widget code
	ctx := r.Context()
	authInfo, err := widgetCodeService.ValidateWidgetCode(ctx, req.Code)
	if err != nil || authInfo == nil {
		httpext.JsonError(w, "Invalid widget code", http.StatusUnauthorized)
		return
	}

	// Verify the client ID matches the one stored with the auth code
	if authInfo.ClientID != req.ClientID {
		httpext.JsonError(w, "Invalid client credentials", http.StatusUnauthorized)
		return
	}

	// Invalidate the used widget code
	if err := widgetCodeService.InvalidateWidgetCode(ctx, req.Code); err != nil {
		log.Error().Err(err).Str("widget_code", req.Code).Msg("Failed to invalidate widget code")
	}

	// Get client config to access scopes
	client := config.GetClientConfig(clientType)

	// Generate JWT token with scopes
	claims := oauth.CustomClaims{
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(jwtLifetime)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			ID:        uuid.New().String(),
		},
		ClientType: clientType,
		GrantType:  "widget",
		Scopes:     client.Scopes,
	}

	issueToken(w, claims)
}

func issueToken(w http.ResponseWriter, claims oauth.CustomClaims) {
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)

	tokenString, err := token.SignedString(config.GetJWTSecret())
	if err != nil {
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
		log.Error().Err(err).Msg("Failed to encode response")
		return
	}
}

func validateClientSecret(provided, stored string) bool {
	return subtle.ConstantTimeCompare([]byte(provided), []byte(stored)) == 1
}

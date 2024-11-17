package handlers

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/deepgram/codename-sage/internal/config"
	"github.com/deepgram/codename-sage/internal/logger"
	"github.com/deepgram/codename-sage/internal/services/auth"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

var (
	sessionStore = auth.NewSessionStore()
	jwtLifetime  = 15 * time.Minute
)

func HandleToken(w http.ResponseWriter, r *http.Request) {
	logger.Debug("Handling token request")
	if r.Method != http.MethodPost {
		logger.Warn("Invalid method: %s", r.Method)
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req auth.TokenRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error("Failed to decode token request: %v", err)
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	logger.Info("Processing token request with grant type: %s", req.GrantType)

	var session auth.Session
	var ok bool

	switch req.GrantType {
	case auth.GrantTypeAnonymous:
		session = sessionStore.CreateSession()
	case auth.GrantTypeRefresh:
		session, ok = sessionStore.RefreshSession(req.RefreshToken)
		if !ok {
			http.Error(w, "Invalid refresh token", http.StatusUnauthorized)
			return
		}
	default:
		http.Error(w, "Invalid grant type", http.StatusBadRequest)
		return
	}

	// Generate JWT
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"sid": session.ID,
		"exp": time.Now().Add(jwtLifetime).Unix(),
		"iat": time.Now().Unix(),
		"jti": uuid.New().String(),
	})

	tokenString, err := token.SignedString(config.GetJWTSecret())
	if err != nil {
		logger.Error("Failed to sign JWT token: %v", err)
		http.Error(w, "Error creating token", http.StatusInternalServerError)
		return
	}

	response := auth.TokenResponse{
		AccessToken:  tokenString,
		TokenType:    "Bearer",
		ExpiresIn:    int(jwtLifetime.Seconds()),
		RefreshToken: session.RefreshToken,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)

	logger.Info("Token generated successfully for session: %s", session.ID)
}

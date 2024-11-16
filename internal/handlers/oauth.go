package handlers

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/deepgram/navi/internal/auth"
	"github.com/deepgram/navi/internal/config"
	"github.com/golang-jwt/jwt/v5"
)

var (
	sessionStore = auth.NewSessionStore()
	jwtLifetime  = 15 * time.Minute
)

func HandleToken(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req auth.TokenRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

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
		"session_id": session.ID,
		"exp":        time.Now().Add(jwtLifetime).Unix(),
		"iat":        time.Now().Unix(),
	})

	tokenString, err := token.SignedString(config.GetJWTSecret())
	if err != nil {
		http.Error(w, "Error creating token", http.StatusInternalServerError)
		return
	}

	response := auth.TokenResponse{
		AccessToken:  tokenString,
		TokenType:    "Bearer",
		ExpiresIn:    int(jwtLifetime.Seconds()),
		RefreshToken: session.RefreshToken,
		SessionID:    session.ID,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

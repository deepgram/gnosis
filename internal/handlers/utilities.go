package handlers

import (
	"fmt"
	"net/http"
	"strings"

	"github.com/deepgram/navi/internal/config"
	"github.com/deepgram/navi/internal/logger"
	"github.com/golang-jwt/jwt/v5"
)

func extractToken(r *http.Request) string {
	authHeader := r.Header.Get("Authorization")
	if authHeader == "" {
		return ""
	}

	parts := strings.Split(authHeader, " ")
	if len(parts) != 2 || parts[0] != "Bearer" {
		return ""
	}

	return parts[1]
}

func validateTokenAndGetSession(tokenString string) (string, bool) {
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			logger.Warn("Unexpected signing method: %v", token.Header["alg"])
			return nil, fmt.Errorf("unexpected signing method")
		}
		return config.GetJWTSecret(), nil
	})

	if err != nil || !token.Valid {
		logger.Warn("Token validation failed: %v", err)
		return "", false
	}

	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return "", false
	}

	sessionID, ok := claims["sid"].(string)
	if !ok {
		return "", false
	}

	return sessionID, true
}

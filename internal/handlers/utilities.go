package handlers

import (
	"fmt"
	"net/http"
	"strings"

	"github.com/deepgram/codename-sage/internal/config"
	"github.com/deepgram/codename-sage/internal/logger"
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

// validateToken validates a token and returns true if it's valid, false otherwise
func validateToken(tokenString string) bool {
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			logger.Warn("Unexpected signing method: %v", token.Header["alg"])
			return nil, fmt.Errorf("unexpected signing method")
		}
		return config.GetJWTSecret(), nil
	})

	if err != nil || !token.Valid {
		logger.Warn("Token validation failed: %v", err)
		return false
	}

	return true
}

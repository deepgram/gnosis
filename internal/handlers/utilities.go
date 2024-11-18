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

// Add this struct to store token validation result
type TokenValidationResult struct {
	Valid      bool
	ClientType string
}

// Update the validateToken function to return client type
func validateToken(tokenString string) TokenValidationResult {
	result := TokenValidationResult{Valid: false}

	token, err := jwt.ParseWithClaims(tokenString, &CustomClaims{}, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			logger.Warn("Unexpected signing method: %v", token.Header["alg"])
			return nil, fmt.Errorf("unexpected signing method")
		}
		return config.GetJWTSecret(), nil
	})

	if err != nil {
		logger.Warn("Token validation failed: %v", err)
		return result
	}

	if claims, ok := token.Claims.(*CustomClaims); ok && token.Valid {
		// Validate client type
		if claims.ClientType == "" {
			logger.Warn("Token missing client type")
			return result
		}

		// Check if client type is valid
		if _, exists := config.AllowedClients[claims.ClientType]; !exists {
			logger.Warn("Invalid client type in token: %s", claims.ClientType)
			return result
		}

		result.Valid = true
		result.ClientType = claims.ClientType
		return result
	}

	logger.Warn("Invalid token claims")
	return result
}

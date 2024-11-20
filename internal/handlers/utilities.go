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
		logger.Debug("No Authorization header found")
		return ""
	}

	parts := strings.Split(authHeader, " ")
	if len(parts) != 2 || parts[0] != "Bearer" {
		logger.Warn("Malformed Authorization header: %s", authHeader)
		return ""
	}

	logger.Debug("Successfully extracted token from Authorization header")
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

	if tokenString == "" {
		logger.Debug("Empty token string provided")
		return result
	}

	token, err := jwt.ParseWithClaims(tokenString, &CustomClaims{}, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			logger.Error("Unexpected signing method: %v", token.Header["alg"])
			return nil, fmt.Errorf("unexpected signing method")
		}
		return config.GetJWTSecret(), nil
	})

	if err != nil {
		logger.Error("Token validation failed: %v", err)
		return result
	}

	if claims, ok := token.Claims.(*CustomClaims); ok && token.Valid {
		// Validate client type
		if claims.ClientType == "" {
			logger.Error("Token missing client type")
			return result
		}

		// Check if client type is valid
		if _, exists := config.AllowedClients[claims.ClientType]; !exists {
			logger.Error("Invalid client type in token: %s", claims.ClientType)
			return result
		}

		logger.Info("Token successfully validated for client type: %s", claims.ClientType)
		result.Valid = true
		result.ClientType = claims.ClientType
		return result
	}

	logger.Error("Invalid token claims")
	return result
}

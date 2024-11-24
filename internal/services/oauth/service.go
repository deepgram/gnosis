package oauth

import (
	"fmt"
	"net/http"
	"strings"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/logger"
	"github.com/golang-jwt/jwt/v5"
)

func ExtractToken(r *http.Request) string {
	authHeader := r.Header.Get("Authorization")
	if authHeader == "" {
		logger.Debug(logger.SERVICE, "No Authorization header found")
		return ""
	}

	parts := strings.Split(authHeader, " ")
	if len(parts) != 2 || parts[0] != "Bearer" {
		logger.Warn(logger.SERVICE, "Malformed Authorization header: %s", authHeader)
		return ""
	}

	logger.Debug(logger.SERVICE, "Successfully extracted token from Authorization header")
	return parts[1]
}

// Add this struct to store token validation result
type TokenValidationResult struct {
	Valid      bool
	ClientType string
}

type CustomClaims struct {
	jwt.RegisteredClaims
	ClientType string `json:"ctp"`
}

// Update the validateToken function to return client type
func ValidateToken(tokenString string) TokenValidationResult {
	result := TokenValidationResult{Valid: false}

	if tokenString == "" {
		logger.Debug(logger.SERVICE, "Empty token string provided")
		return result
	}

	token, err := jwt.ParseWithClaims(tokenString, &CustomClaims{}, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			logger.Error(logger.SERVICE, "Unexpected signing method: %v", token.Header["alg"])
			return nil, fmt.Errorf("unexpected signing method")
		}
		return config.GetJWTSecret(), nil
	})

	if err != nil {
		logger.Error(logger.SERVICE, "Token validation failed: %v", err)
		return result
	}

	if claims, ok := token.Claims.(*CustomClaims); ok && token.Valid {
		// Validate client type
		if claims.ClientType == "" {
			logger.Error(logger.SERVICE, "Token missing client type")
			return result
		}

		// Check if client type is valid
		if _, exists := config.AllowedClients[claims.ClientType]; !exists {
			logger.Error(logger.SERVICE, "Invalid client type in token: %s", claims.ClientType)
			return result
		}

		logger.Info(logger.SERVICE, "Token successfully validated for client type: %s", claims.ClientType)
		result.Valid = true
		result.ClientType = claims.ClientType
		return result
	}

	logger.Error(logger.SERVICE, "Invalid token claims")
	return result
}

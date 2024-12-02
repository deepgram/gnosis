package oauth

import (
	"net/http"
	"strings"
	"time"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/golang-jwt/jwt/v5"
)

func ExtractToken(r *http.Request) string {
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
	GrantType  string
	ExpiresAt  time.Time
	Scopes     []string
}

type CustomClaims struct {
	jwt.RegisteredClaims
	ClientType string   `json:"ctp"`
	GrantType  string   `json:"gty"`
	Scopes     []string `json:"scp"`
}

// Update the validateToken function to return client type
func ValidateToken(tokenString string) TokenValidationResult {
	result := TokenValidationResult{Valid: false}

	// Parse token
	token, err := jwt.ParseWithClaims(tokenString, &CustomClaims{}, func(token *jwt.Token) (interface{}, error) {
		return config.GetJWTSecret(), nil
	})

	if err != nil {
		return result
	}

	if claims, ok := token.Claims.(*CustomClaims); ok && token.Valid {
		// Validate client type
		if claims.ClientType == "" {
			return result
		}

		// Validate grant type
		if claims.GrantType != "client_credentials" && claims.GrantType != "widget" {
			return result
		}

		result.Valid = true
		result.ClientType = claims.ClientType
		result.GrantType = claims.GrantType
		result.ExpiresAt = claims.ExpiresAt.Time
		result.Scopes = claims.Scopes
		return result
	}

	return result
}

package oauth

import (
	"net/http"
	"strings"
	"time"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/golang-jwt/jwt/v5"
)

// ExtractToken extracts the bearer token from either the Sec-WebSocket-Protocol header
// or Authorization header in the request. For WebSocket connections, it expects the
// Sec-WebSocket-Protocol header to contain ["bearer", "JWT_TOKEN"]. For regular HTTP
// requests, it checks the Authorization header for a bearer token. If neither header
// contains a valid token, an empty string is returned.
func ExtractToken(r *http.Request) string {
	// First check WebSocket protocol header
	wsProtocol := r.Header.Get("Sec-WebSocket-Protocol")
	if wsProtocol != "" {
		protocols := strings.Split(wsProtocol, ", ")
		// Find index of "bearer" protocol
		bearerIndex := -1
		for i, protocol := range protocols {
			if strings.ToLower(protocol) == "bearer" {
				bearerIndex = i
				break
			}
		}

		// Check if we found bearer and there's a token after it
		if bearerIndex >= 0 && len(protocols) > bearerIndex+1 {
			// Set Authorization header for downstream processing
			r.Header.Set("Authorization", "Bearer "+protocols[bearerIndex+1])
			return protocols[bearerIndex+1]
		}
	}

	// Fall back to checking Authorization header
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
// ValidateTestToken validates a test token with basic claims for testing purposes
func ValidateTestToken(tokenString string) TokenValidationResult {
	result := TokenValidationResult{
		Valid:      true,
		ClientType: "test",
		GrantType:  "client_credentials",
		ExpiresAt:  time.Now().Add(24 * time.Hour),
		Scopes:     []string{"chat:write"},
	}
	return result
}

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

package middleware

import (
	"context"
	"net/http"

	"github.com/deepgram/gnosis/internal/services/oauth"
	"github.com/deepgram/gnosis/pkg/httpext"
	"github.com/deepgram/gnosis/pkg/logger"
)

type contextKey string

const (
	tokenValidationKey contextKey = "tokenValidation"
)

func RequireAuth(allowedGrants []string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			tokenString := oauth.ExtractToken(r)
			if tokenString == "" {
				logger.Warn(logger.MIDDLEWARE, "Missing authorization token")
				httpext.JsonError(w, "Unauthorized", http.StatusUnauthorized)
				return
			}

			validation := oauth.ValidateToken(tokenString)
			if !validation.Valid {
				logger.Warn(logger.MIDDLEWARE, "Invalid authorization token")
				httpext.JsonError(w, "Invalid token", http.StatusUnauthorized)
				return
			}

			// Validate grant type
			grantAllowed := false
			for _, grant := range allowedGrants {
				if validation.GrantType == grant {
					grantAllowed = true
					break
				}
			}

			if !grantAllowed {
				logger.Warn(logger.MIDDLEWARE, "Unauthorized grant type: %s", validation.GrantType)
				httpext.JsonError(w, "Unauthorized grant type", http.StatusForbidden)
				return
			}

			// Store validation result in context
			ctx := context.WithValue(r.Context(), tokenValidationKey, &validation)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

func RequireScope(scope string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			// Get validation result from context
			validation, ok := r.Context().Value(tokenValidationKey).(*oauth.TokenValidationResult)
			if !ok || validation == nil {
				logger.Error(logger.MIDDLEWARE, "Token validation missing from context")
				httpext.JsonError(w, "Internal server error", http.StatusInternalServerError)
				return
			}

			// Check if token has required scope
			hasScope := false
			for _, s := range validation.Scopes {
				if s == scope {
					hasScope = true
					break
				}
			}

			if !hasScope {
				logger.Warn(logger.MIDDLEWARE, "Client %s missing required scope: %s", validation.ClientType, scope)
				httpext.JsonError(w, "Insufficient scope", http.StatusForbidden)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

// GetTokenValidation retrieves the token validation result from the request context
func GetTokenValidation(r *http.Request) *oauth.TokenValidationResult {
	if validation, ok := r.Context().Value(tokenValidationKey).(*oauth.TokenValidationResult); ok {
		return validation
	}
	return nil
}

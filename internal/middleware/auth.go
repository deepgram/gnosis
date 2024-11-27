package middleware

import (
	"net/http"

	"github.com/deepgram/gnosis/internal/logger"
	"github.com/deepgram/gnosis/internal/services/oauth"
)

func RequireAuth(allowedGrants []string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			tokenString := oauth.ExtractToken(r)
			if tokenString == "" {
				logger.Warn(logger.MIDDLEWARE, "Missing authorization token")
				http.Error(w, "Unauthorized", http.StatusUnauthorized)
				return
			}

			validation := oauth.ValidateToken(tokenString)
			if !validation.Valid {
				logger.Warn(logger.MIDDLEWARE, "Invalid authorization token")
				http.Error(w, "Invalid token", http.StatusUnauthorized)
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
				http.Error(w, "Unauthorized grant type", http.StatusForbidden)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

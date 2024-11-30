package middleware

import (
	"net/http"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/pkg/httpext"
	"github.com/deepgram/gnosis/pkg/logger"
	"github.com/deepgram/gnosis/pkg/ratelimit"
)

func RateLimit(limitKey string) func(http.Handler) http.Handler {
	cfg := config.GetRateLimitConfig(limitKey)
	limiter := ratelimit.NewLimiter(cfg.Window, cfg.MaxHits)

	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if !cfg.Enabled {
				next.ServeHTTP(w, r)
				return
			}

			// Use X-Forwarded-For if behind proxy, otherwise remote address
			ip := r.Header.Get("X-Forwarded-For")
			if ip == "" {
				ip = r.RemoteAddr
			}

			if !limiter.Allow(ip) {
				logger.Warn(logger.MIDDLEWARE, "Rate limit exceeded for %s on %s", ip, limitKey)
				httpext.JsonError(w, "Rate limit exceeded", http.StatusTooManyRequests)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

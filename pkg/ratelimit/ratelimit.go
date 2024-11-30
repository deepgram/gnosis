package ratelimit

import (
	"sync"
	"time"
)

type Limiter struct {
	mu      sync.RWMutex
	limits  map[string][]time.Time
	window  time.Duration
	maxHits int
}

func NewLimiter(window time.Duration, maxHits int) *Limiter {
	return &Limiter{
		limits:  make(map[string][]time.Time),
		window:  window,
		maxHits: maxHits,
	}
}

func (l *Limiter) Allow(key string) bool {
	l.mu.Lock()
	defer l.mu.Unlock()

	now := time.Now()
	windowStart := now.Add(-l.window)

	// Clean old entries
	if hits, exists := l.limits[key]; exists {
		valid := hits[:0]
		for _, hit := range hits {
			if hit.After(windowStart) {
				valid = append(valid, hit)
			}
		}
		l.limits[key] = valid
	}

	// Check current count
	if len(l.limits[key]) >= l.maxHits {
		return false
	}

	// Add new hit
	l.limits[key] = append(l.limits[key], now)
	return true
}

package auth

import (
	"time"
)

type Session struct {
	ID           string    `json:"id"`
	RefreshToken string    `json:"refresh_token"`
	CreatedAt    time.Time `json:"created_at"`
	ExpiresAt    time.Time `json:"expires_at"`
}

type TokenResponse struct {
	AccessToken  string `json:"access_token"`
	TokenType    string `json:"token_type"`
	ExpiresIn    int    `json:"expires_in"`
	RefreshToken string `json:"refresh_token"`
}

type TokenRequest struct {
	GrantType    string `json:"grant_type"`
	RefreshToken string `json:"refresh_token,omitempty"`
}

const (
	GrantTypeAnonymous = "anonymous"
	GrantTypeRefresh   = "refresh_token"
)

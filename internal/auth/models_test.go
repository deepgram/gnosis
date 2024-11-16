package auth

import (
	"encoding/json"
	"testing"
	"time"
)

func TestSessionJSON(t *testing.T) {
	now := time.Now()
	session := Session{
		ID:           "test-id",
		RefreshToken: "test-refresh-token",
		CreatedAt:    now,
		ExpiresAt:    now.Add(24 * time.Hour),
	}

	t.Run("marshal session", func(t *testing.T) {
		data, err := json.Marshal(session)
		if err != nil {
			t.Fatalf("Failed to marshal session: %v", err)
		}

		var unmarshaled Session
		if err := json.Unmarshal(data, &unmarshaled); err != nil {
			t.Fatalf("Failed to unmarshal session: %v", err)
		}

		if unmarshaled.ID != session.ID {
			t.Errorf("Got ID %s, want %s", unmarshaled.ID, session.ID)
		}
		if unmarshaled.RefreshToken != session.RefreshToken {
			t.Errorf("Got refresh token %s, want %s",
				unmarshaled.RefreshToken, session.RefreshToken)
		}
	})
}

func TestTokenRequestJSON(t *testing.T) {
	tests := []struct {
		name    string
		request TokenRequest
		want    string
	}{
		{
			name: "anonymous grant",
			request: TokenRequest{
				GrantType: GrantTypeAnonymous,
			},
			want: `{"grant_type":"anonymous","refresh_token":""}`,
		},
		{
			name: "refresh grant",
			request: TokenRequest{
				GrantType:    GrantTypeRefresh,
				RefreshToken: "test-token",
			},
			want: `{"grant_type":"refresh_token","refresh_token":"test-token"}`,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			data, err := json.Marshal(tt.request)
			if err != nil {
				t.Fatalf("Failed to marshal request: %v", err)
			}

			if string(data) != tt.want {
				t.Errorf("Got JSON %s, want %s", string(data), tt.want)
			}

			var unmarshaled TokenRequest
			if err := json.Unmarshal(data, &unmarshaled); err != nil {
				t.Fatalf("Failed to unmarshal request: %v", err)
			}

			if unmarshaled.GrantType != tt.request.GrantType {
				t.Errorf("Got grant type %s, want %s",
					unmarshaled.GrantType, tt.request.GrantType)
			}
			if unmarshaled.RefreshToken != tt.request.RefreshToken {
				t.Errorf("Got refresh token %s, want %s",
					unmarshaled.RefreshToken, tt.request.RefreshToken)
			}
		})
	}
}

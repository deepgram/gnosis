package config

import (
	"os"
	"testing"
)

func TestGetEnvOrDefault(t *testing.T) {
	tests := []struct {
		name         string
		key          string
		defaultValue string
		envValue     string
		want         string
	}{
		{
			name:         "returns default when env not set",
			key:          "TEST_KEY_1",
			defaultValue: "default",
			envValue:     "",
			want:         "default",
		},
		{
			name:         "returns env value when set",
			key:          "TEST_KEY_2",
			defaultValue: "default",
			envValue:     "custom",
			want:         "custom",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.envValue != "" {
				os.Setenv(tt.key, tt.envValue)
				defer os.Unsetenv(tt.key)
			}

			got := getEnvOrDefault(tt.key, tt.defaultValue)
			if got != tt.want {
				t.Errorf("getEnvOrDefault() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestJWTSecretManagement(t *testing.T) {
	originalSecret := GetJWTSecret()
	newSecret := []byte("test-secret")

	t.Run("set and restore JWT secret", func(t *testing.T) {
		restore := SetJWTSecret(newSecret)

		if string(GetJWTSecret()) != string(newSecret) {
			t.Errorf("JWT secret not updated, got %s, want %s",
				string(GetJWTSecret()), string(newSecret))
		}

		restore()

		if string(GetJWTSecret()) != string(originalSecret) {
			t.Errorf("JWT secret not restored, got %s, want %s",
				string(GetJWTSecret()), string(originalSecret))
		}
	})

	t.Run("concurrent access to JWT secret", func(t *testing.T) {
		done := make(chan bool)
		for i := 0; i < 10; i++ {
			go func() {
				GetJWTSecret()
				done <- true
			}()
		}

		for i := 0; i < 10; i++ {
			<-done
		}
	})
}

package config

import (
	"os"
	"testing"
)

func TestScanForClientConfigs(t *testing.T) {
	tests := []struct {
		name     string
		envVars  map[string]string
		expected map[string]ClientConfig
	}{
		{
			name: "widget_client",
			envVars: map[string]string{
				"GNOSIS_WIDGET_CLIENT_ID":    "widget-id",
				"GNOSIS_WIDGET_NO_SECRET":    "true",
				"GNOSIS_WIDGET_ALLOWED_URLS": "https://example.com,https://test.com",
				"GNOSIS_WIDGET_SCOPES":       "read,write",
			},
			expected: map[string]ClientConfig{
				"widget": {
					ID:          "widget-id",
					NoSecret:    true,
					AllowedURLs: []string{"https://example.com", "https://test.com"},
					Scopes:      []string{"read", "write"},
				},
			},
		},
		{
			name: "multiple_clients",
			envVars: map[string]string{
				"GNOSIS_APP1_CLIENT_ID":     "app1-id",
				"GNOSIS_APP1_CLIENT_SECRET": "app1-secret",
				"GNOSIS_APP1_SCOPES":        "scope1,scope2",
				"GNOSIS_APP2_CLIENT_ID":     "app2-id",
				"GNOSIS_APP2_NO_SECRET":     "true",
				"GNOSIS_APP2_ALLOWED_URLS":  "https://app2.com",
			},
			expected: map[string]ClientConfig{
				"app1": {
					ID:     "app1-id",
					Secret: "app1-secret",
					Scopes: []string{"scope1", "scope2"},
				},
				"app2": {
					ID:          "app2-id",
					NoSecret:    true,
					AllowedURLs: []string{"https://app2.com"},
				},
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Clear all environment variables before each test
			os.Clearenv()

			// Set up environment for this test
			for k, v := range tt.envVars {
				if err := os.Setenv(k, v); err != nil {
					t.Fatalf("Failed to set environment variable %s: %v", k, err)
				}
			}

			// Clean up environment after test
			defer func() {
				for k := range tt.envVars {
					os.Unsetenv(k)
				}
			}()

			// Run the scan
			got := scanForClientConfigs()

			// Compare results
			if len(got) != len(tt.expected) {
				t.Errorf("scanForClientConfigs() got %d clients, expected %d", len(got), len(tt.expected))
				t.Logf("Got clients: %+v", got)
				t.Logf("Expected clients: %+v", tt.expected)
				return
			}

			for clientType, expectedConfig := range tt.expected {
				gotConfig, exists := got[clientType]
				if !exists {
					t.Errorf("Expected client %s not found", clientType)
					continue
				}

				if gotConfig.ID != expectedConfig.ID {
					t.Errorf("Client %s ID = %v, expected %v", clientType, gotConfig.ID, expectedConfig.ID)
				}
				if gotConfig.Secret != expectedConfig.Secret {
					t.Errorf("Client %s Secret = %v, expected %v", clientType, gotConfig.Secret, expectedConfig.Secret)
				}
				if gotConfig.NoSecret != expectedConfig.NoSecret {
					t.Errorf("Client %s NoSecret = %v, expected %v", clientType, gotConfig.NoSecret, expectedConfig.NoSecret)
				}
			}
		})
	}
}

package chat

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/deepgram/gnosis/internal/infrastructure/openai"
	"github.com/deepgram/gnosis/internal/services/chat"
	chatModels "github.com/deepgram/gnosis/internal/services/chat/models"
	"github.com/deepgram/gnosis/internal/services/tools"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

// MockOpenAIService mocks the OpenAI service
type MockOpenAIService struct {
	*openai.Service // Embed the actual service type
	mock.Mock
}

func NewMockOpenAIService() *MockOpenAIService {
	return &MockOpenAIService{
		Service: &openai.Service{},
	}
}

// MockToolService mocks the tool service
type MockToolService struct {
	*tools.Service // Embed the actual service type
	mock.Mock
}

func NewMockToolService() *MockToolService {
	return &MockToolService{
		Service: &tools.Service{},
	}
}

func TestHandleChatCompletions(t *testing.T) {
	tests := []struct {
		name           string
		requestBody    interface{}
		expectedStatus int
		setupMocks     func(*MockOpenAIService, *MockToolService)
	}{
		{
			name: "Valid request with successful response",
			requestBody: map[string]interface{}{
				"messages": []map[string]string{
					{
						"role":    "user",
						"content": "Hello!",
					},
				},
				"config": map[string]interface{}{
					"temperature":      0.7,
					"max_tokens":       1000,
					"top_p":            1.0,
					"presence_penalty": 0.0,
				},
			},
			expectedStatus: http.StatusOK,
			setupMocks: func(mockOpenAI *MockOpenAIService, mockTools *MockToolService) {
				mockOpenAI.On("GetClient").Return(&openai.Service{})
				mockTools.On("GetOpenAITools").Return(nil)
				mockTools.On("GetToolExecutor").Return(nil)
			},
		},
		{
			name: "Invalid request - empty messages",
			requestBody: map[string]interface{}{
				"messages": []map[string]string{},
			},
			expectedStatus: http.StatusBadRequest,
			setupMocks: func(mockOpenAI *MockOpenAIService, mockTools *MockToolService) {
				// No mock setup needed for invalid request
			},
		},
		{
			name:           "Invalid request - malformed JSON",
			requestBody:    "invalid json",
			expectedStatus: http.StatusBadRequest,
			setupMocks: func(mockOpenAI *MockOpenAIService, mockTools *MockToolService) {
				// No mock setup needed for invalid request
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Initialize mocks with proper types
			mockOpenAI := NewMockOpenAIService()
			mockTools := NewMockToolService()

			// Setup mocks if needed
			if tt.setupMocks != nil {
				tt.setupMocks(mockOpenAI, mockTools)
			}

			// Initialize chat service with mocks - now type-compatible
			chatService, err := chat.NewService(mockOpenAI.Service, mockTools.Service)
			assert.NoError(t, err)

			// Create request body
			var body bytes.Buffer
			if str, ok := tt.requestBody.(string); ok {
				body.WriteString(str)
			} else {
				err := json.NewEncoder(&body).Encode(tt.requestBody)
				assert.NoError(t, err)
			}

			// Create request
			req := httptest.NewRequest(http.MethodPost, "/v1/chat/completions", &body)
			req.Header.Set("Content-Type", "application/json")
			w := httptest.NewRecorder()

			// Handle request
			HandleChatCompletions(chatService, w, req)

			// Assert response
			assert.Equal(t, tt.expectedStatus, w.Code)

			// Verify mocks
			mockOpenAI.AssertExpectations(t)
			mockTools.AssertExpectations(t)

			// Additional assertions for successful responses
			if tt.expectedStatus == http.StatusOK {
				var response chatModels.ChatResponse
				err := json.NewDecoder(w.Body).Decode(&response)
				assert.NoError(t, err)
				assert.NotEmpty(t, response.ID)
				assert.NotEmpty(t, response.Created)
				assert.NotEmpty(t, response.Choices)
			}
		})
	}
}

func TestChatServiceIntegration(t *testing.T) {
	// Reference the chat service implementation
	chatServiceImpl := &chat.Implementation{}

	tests := []struct {
		name          string
		messages      []chatModels.ChatMessage
		config        *chatModels.ChatConfig
		expectedError bool
	}{
		{
			name: "Basic chat completion",
			messages: []chatModels.ChatMessage{
				{
					Role:    "user",
					Content: "What are Deepgram's products?",
				},
			},
			config: &chatModels.ChatConfig{
				Temperature: 0.7,
				MaxTokens:   1000,
			},
			expectedError: false,
		},
		{
			name: "Chat completion with system message",
			messages: []chatModels.ChatMessage{
				{
					Role:    "system",
					Content: "You are a helpful assistant.",
				},
				{
					Role:    "user",
					Content: "Tell me about Deepgram's transcription service.",
				},
			},
			config: &chatModels.ChatConfig{
				Temperature: 0.5,
				MaxTokens:   2000,
			},
			expectedError: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ctx := context.Background()
			response, err := chatServiceImpl.ProcessChat(ctx, tt.messages, tt.config)

			if tt.expectedError {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
				assert.NotNil(t, response)
				if response != nil {
					assert.NotEmpty(t, response.ID)
					assert.NotEmpty(t, response.Choices)
					assert.Greater(t, response.Usage.TotalTokens, 0)
				}
			}
		})
	}
}

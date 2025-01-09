package chat

import (
	"context"

	"github.com/sashabaranov/go-openai"
)

// Service defines the interface for chat operations
type Service interface {
	// ProcessChat processes a chat conversation and returns a response
	ProcessChat(ctx context.Context, req openai.ChatCompletionRequest) (*openai.ChatCompletionResponse, error)
}

// Repository defines the interface for chat storage operations
// type Repository interface {
// 	// SaveChat saves a chat conversation
// 	SaveChat(ctx context.Context, messages []models.ChatMessage, response *models.ChatResponse) error

// 	// GetChat retrieves a chat conversation by ID
// 	GetChat(ctx context.Context, chatID string) ([]models.ChatMessage, error)
// }

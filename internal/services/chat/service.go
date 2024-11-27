package chat

import (
	"context"

	"github.com/deepgram/gnosis/internal/services/chat/models"
)

// Service defines the interface for chat operations
type Service interface {
	// ProcessChat processes a chat conversation and returns a response
	ProcessChat(ctx context.Context, messages []models.ChatMessage, config *models.ChatConfig) (*models.ChatResponse, error)
}

// Repository defines the interface for chat storage operations
// type Repository interface {
// 	// SaveChat saves a chat conversation
// 	SaveChat(ctx context.Context, messages []models.ChatMessage, response *models.ChatResponse) error

// 	// GetChat retrieves a chat conversation by ID
// 	GetChat(ctx context.Context, chatID string) ([]models.ChatMessage, error)
// }

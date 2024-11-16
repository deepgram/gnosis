package assistant

// UserMessage represents an incoming message from the user
type UserMessage struct {
	Content   string `json:"content"`
	MessageID string `json:"message_id,omitempty"`
}

// AssistantResponse represents a response from the assistant
type AssistantResponse struct {
	RequestID string `json:"request_id"`
	MessageID string `json:"message_id,omitempty"`
	Content   string `json:"content"`
	Status    string `json:"status"` // "streaming", "complete", or "error"
}

// ResponseStatus defines the possible states of an assistant response
const (
	StatusStreaming = "streaming"
	StatusComplete  = "complete"
	StatusError     = "error"
)

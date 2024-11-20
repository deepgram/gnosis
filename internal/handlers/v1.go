package handlers

import (
	"net/http"

	v1 "github.com/deepgram/codename-sage/internal/handlers/v1"
)

// v1/oauth.go
func HandleTokenV1(w http.ResponseWriter, r *http.Request) {
	v1.HandleToken(w, r)
}

// v1/chat.go
func HandleChatCompletionV1(w http.ResponseWriter, r *http.Request) {
	v1.HandleChatCompletion(w, r)
}

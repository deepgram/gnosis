package handlers

import (
	"net/http"

	v1 "github.com/deepgram/gnosis/internal/handlers/v1"
	"github.com/deepgram/gnosis/internal/services/authcode"
	"github.com/deepgram/gnosis/internal/services/chat"
)

// v1/oauth.go
func HandleTokenV1(w http.ResponseWriter, r *http.Request) {
	v1.HandleToken(w, r)
}

// v1/chat.go
func HandleChatCompletionV1(chatService *chat.Service, w http.ResponseWriter, r *http.Request) {
	v1.HandleChatCompletion(chatService, w, r)
}

// Add this function
func HandleAuthorizeV1(authCodeService *authcode.Service, w http.ResponseWriter, r *http.Request) {
	v1.HandleAuthorize(authCodeService, w, r)
}

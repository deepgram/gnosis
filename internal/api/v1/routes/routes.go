package routes

import (
	"net/http"

	v1handlers "github.com/deepgram/gnosis/internal/api/v1/handlers"
	"github.com/deepgram/gnosis/internal/services/authcode"
	"github.com/deepgram/gnosis/internal/services/chat"
)

// v1/oauth.go
func HandleTokenV1(authCodeService *authcode.Service, w http.ResponseWriter, r *http.Request) {
	v1handlers.HandleToken(authCodeService, w, r)
}

// v1/chat.go
func HandleChatCompletionV1(chatService *chat.Service, w http.ResponseWriter, r *http.Request) {
	v1handlers.HandleChatCompletion(chatService, w, r)
}

// Add this function
func HandleAuthorizeV1(authCodeService *authcode.Service, w http.ResponseWriter, r *http.Request) {
	v1handlers.HandleAuthorize(authCodeService, w, r)
}

func HandleWidgetJSV1(w http.ResponseWriter, r *http.Request) {
	v1handlers.HandleWidgetJS(w, r)
}

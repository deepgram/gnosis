package handlers

import (
	"net/http"

	"github.com/deepgram/gnosis/internal/services/authcode"
)

// v1/oauth.go
func HandleTokenV1(authCodeService *authcode.Service, w http.ResponseWriter, r *http.Request) {
	HandleToken(authCodeService, w, r)
}

// Add this function
func HandleAuthorizeV1(authCodeService *authcode.Service, w http.ResponseWriter, r *http.Request) {
	HandleAuthorize(authCodeService, w, r)
}

func HandleWidgetJSV1(w http.ResponseWriter, r *http.Request) {
	HandleWidgetJS(w, r)
}

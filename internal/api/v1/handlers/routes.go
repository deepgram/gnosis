package handlers

import (
	"net/http"

	v1oauth "github.com/deepgram/gnosis/internal/api/v1/handlers/oauth"
	v1mware "github.com/deepgram/gnosis/internal/api/v1/middleware"
	"github.com/deepgram/gnosis/internal/services"
	"github.com/gorilla/mux"
)

func RegisterV1Routes(router *mux.Router, services *services.Services) {
	// v1 routes
	v1 := router.PathPrefix("/v1").Subrouter()

	// Public v1 routes (no auth required)
	v1publicRouter := v1.NewRoute().Subrouter()
	v1publicRouter.HandleFunc("/widget.js", func(w http.ResponseWriter, r *http.Request) {
		HandleWidgetJS(services.GetSessionService(), w, r)
	}).Methods("GET")

	// OAuth v1 routes (no auth required)
	v1oauthRouter := v1.PathPrefix("/oauth").Subrouter()
	v1oauthRouter.Handle("/token", v1mware.RateLimit("oauth_token")(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		v1oauth.HandleToken(services.GetWidgetCodeService(), w, r)
	}))).Methods("POST")
	v1oauthRouter.Handle("/widget", v1mware.RateLimit("oauth_widget")(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		v1oauth.HandleWidgetAuth(services.GetWidgetCodeService(), w, r)
	}))).Methods("POST")

	// Protected v1 routes (require auth)
	v1protectedRouter := v1.NewRoute().Subrouter()
	v1protectedRouter.Use(v1mware.RequireAuth([]string{"client_credentials", "widget"}))

	// Protected v1 chat routes
	v1chatRouter := v1protectedRouter.PathPrefix("/chat").Subrouter()
	v1chatRouter.Use(v1mware.RequireScope("chat:write"))
	v1chatRouter.Handle("/completions", v1mware.RateLimit("chat_completion")(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		HandleChatCompletion(services.GetChatService(), w, r)
	}))).Methods("POST")
}

package handlers

import (
	"net/http"

	"github.com/deepgram/gnosis/internal/api/v1/handlers/chat"
	"github.com/deepgram/gnosis/internal/api/v1/handlers/oauth"
	"github.com/deepgram/gnosis/internal/api/v1/handlers/websocket"
	"github.com/deepgram/gnosis/internal/api/v1/handlers/widget"
	"github.com/deepgram/gnosis/internal/api/v1/middleware"
	"github.com/deepgram/gnosis/internal/services"

	"github.com/gorilla/mux"
)

func RegisterV1Routes(router *mux.Router, services *services.Services) {
	// v1 routes
	v1 := router.PathPrefix("/v1").Subrouter()

	// Public v1 routes (no auth required)
	publicRoutes := v1.NewRoute().Subrouter()
	publicRoutes.HandleFunc("/widget.js", func(w http.ResponseWriter, r *http.Request) {
		widget.HandleWidgetJS(services.GetSessionService(), w, r)
	}).Methods("GET")

	// OAuth v1 routes (no auth required)
	oauthRoutes := v1.PathPrefix("/oauth").Subrouter()
	oauthRoutes.HandleFunc("/token", func(w http.ResponseWriter, r *http.Request) {
		oauth.HandleToken(services.GetWidgetCodeService(), w, r)
	}).Methods("POST")
	oauthRoutes.HandleFunc("/widget", func(w http.ResponseWriter, r *http.Request) {
		oauth.HandleWidgetAuth(services.GetWidgetCodeService(), w, r)
	}).Methods("POST")

	// Protected v1 routes (require auth)
	protectedRoutes := v1.NewRoute().Subrouter()
	// protectedRoutes.Use(v1mware.RequireAuth([]string{"client_credentials", "widget"}))

	// Protected v1 agent routes
	agentRoutes := protectedRoutes.NewRoute().Subrouter()
	agentRoutes.HandleFunc("/agent", websocket.HandleAgentWebSocket)

	// Protected v1 chat routes
	chatRoutes := protectedRoutes.PathPrefix("/chat").Subrouter()
	chatRoutes.Use(middleware.RequireScope("chat:write"))
	chatRoutes.HandleFunc("/completions", func(w http.ResponseWriter, r *http.Request) {
		chat.HandleChatCompletions(services.GetChatService(), w, r)
	}).Methods("POST")
}

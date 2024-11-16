package main

import (
	"log"
	"net/http"

	"github.com/deepgram/navi/internal/handlers"
	"github.com/gorilla/mux"
)

func main() {
	r := mux.NewRouter()

	// OAuth endpoints
	r.HandleFunc("/oauth/token", handlers.HandleToken).Methods("POST")

	// WebSocket endpoint
	r.HandleFunc("/ws", handlers.HandleWebSocket)

	log.Println("Server starting on :8080")
	if err := http.ListenAndServe(":8080", r); err != nil {
		log.Fatal("ListenAndServe error:", err)
	}
}

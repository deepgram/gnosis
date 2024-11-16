package main

import (
	"log"
	"net/http"

	"github.com/deepgram/navi/internal/handlers"
	"github.com/gorilla/mux"
)

func main() {
	r := setupRouter()

	log.Println("Server starting on :8080")
	if err := http.ListenAndServe(":8080", r); err != nil {
		log.Fatal("ListenAndServe error:", err)
	}
}

func setupRouter() *mux.Router {
	r := mux.NewRouter()
	r.HandleFunc("/oauth/token", handlers.HandleToken).Methods("POST")
	r.HandleFunc("/ws", handlers.HandleWebSocket)
	return r
}

package handlers

import (
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/deepgram/navi/internal/config"
	"github.com/deepgram/navi/internal/connections"
	"github.com/golang-jwt/jwt/v5"
	"github.com/gorilla/websocket"
)

var (
	manager  = connections.NewManager(connections.DefaultTimeouts)
	upgrader = websocket.Upgrader{
		ReadBufferSize:  1024,
		WriteBufferSize: 1024,
		CheckOrigin: func(r *http.Request) bool {
			return true // In production, implement proper origin checking
		},
	}
)

func extractToken(r *http.Request) string {
	authHeader := r.Header.Get("Authorization")
	if authHeader == "" {
		return ""
	}

	parts := strings.Split(authHeader, " ")
	if len(parts) != 2 || parts[0] != "Bearer" {
		return ""
	}

	return parts[1]
}

func validateTokenAndGetSession(tokenString string) (string, bool) {
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		return config.GetJWTSecret(), nil
	})

	if err != nil || !token.Valid {
		return "", false
	}

	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return "", false
	}

	sessionID, ok := claims["sid"].(string)
	if !ok {
		return "", false
	}

	return sessionID, true
}

func HandleWebSocket(w http.ResponseWriter, r *http.Request) {
	tokenString := extractToken(r)
	if tokenString == "" {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	// sessionID, valid := validateTokenAndGetSession(tokenString)
	_, valid := validateTokenAndGetSession(tokenString)
	if !valid {
		http.Error(w, "Invalid token", http.StatusUnauthorized)
		return
	}

	// fmt.Println("Session ID:", sessionID)

	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		http.Error(w, "Could not upgrade connection", http.StatusInternalServerError)
		return
	}

	manager.AddConnection(conn)
	defer manager.RemoveConnection(conn)

	// Set up ping/pong handlers
	conn.SetReadDeadline(time.Now().Add(manager.GetTimeouts().PongWait))
	conn.SetPongHandler(func(string) error {
		return conn.SetReadDeadline(time.Now().Add(manager.GetTimeouts().PongWait))
	})

	// Start ping ticker in separate goroutine
	done := make(chan struct{})
	defer close(done)

	go func() {
		ticker := time.NewTicker(manager.GetTimeouts().PingPeriod)
		defer ticker.Stop()

		for {
			select {
			case <-ticker.C:
				deadline := time.Now().Add(manager.GetTimeouts().WriteWait)
				err := conn.WriteControl(websocket.PingMessage, []byte{}, deadline)
				if err != nil {
					return
				}
			case <-done:
				return
			}
		}
	}()

	// Send initial message
	if err := conn.WriteMessage(websocket.TextMessage, []byte("Connected")); err != nil {
		return
	}

	// Message handling loop
	for {
		conn.SetReadDeadline(time.Now().Add(manager.GetTimeouts().PongWait))
		messageType, message, err := conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err,
				websocket.CloseGoingAway,
				websocket.CloseAbnormalClosure,
				websocket.CloseNormalClosure) {
				log.Printf("Error reading message: %v", err)
			}
			break
		}

		// Handle close messages
		if messageType == websocket.CloseMessage {
			break
		}

		// Only process text messages as JSON
		if messageType == websocket.TextMessage {
			if err := HandleAssistantMessage(conn, messageType, message); err != nil {
				log.Printf("Error handling assistant message: %v", err)
				break
			}
		}
	}
}

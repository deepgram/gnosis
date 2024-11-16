package handlers

import (
	"fmt"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/deepgram/navi/internal/config"
	"github.com/golang-jwt/jwt/v5"
	"github.com/gorilla/websocket"
)

type TimeoutConfig struct {
	PongWait   time.Duration
	PingPeriod time.Duration
	WriteWait  time.Duration
}

type ConnectionManager struct {
	connections sync.Map
}

var (
	defaultTimeouts = TimeoutConfig{
		PongWait:   30 * time.Second,
		PingPeriod: 27 * time.Second, // (PongWait * 9) / 10
		WriteWait:  10 * time.Second,
	}

	currentTimeouts = defaultTimeouts

	manager  = &ConnectionManager{}
	upgrader = websocket.Upgrader{
		ReadBufferSize:  1024,
		WriteBufferSize: 1024,
		CheckOrigin: func(r *http.Request) bool {
			return true // In production, implement proper origin checking
		},
	}
)

func SetTimeouts(timeouts TimeoutConfig) func() {
	previous := currentTimeouts
	currentTimeouts = timeouts
	return func() {
		currentTimeouts = previous
	}
}

func (cm *ConnectionManager) addConnection(conn *websocket.Conn) {
	cm.connections.Store(conn, struct{}{})
}

func (cm *ConnectionManager) removeConnection(conn *websocket.Conn) {
	cm.connections.Delete(conn)
}

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

	sessionID, valid := validateTokenAndGetSession(tokenString)
	if !valid {
		http.Error(w, "Invalid token", http.StatusUnauthorized)
		return
	}

	fmt.Println("Session ID:", sessionID)

	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		http.Error(w, "Could not upgrade connection", http.StatusInternalServerError)
		return
	}

	manager.addConnection(conn)
	defer func() {
		manager.removeConnection(conn)
		conn.Close()
	}()

	// Set up ping/pong handlers
	conn.SetReadDeadline(time.Now().Add(currentTimeouts.PongWait))
	conn.SetPongHandler(func(string) error {
		return conn.SetReadDeadline(time.Now().Add(currentTimeouts.PongWait))
	})

	// Start ping ticker in separate goroutine
	done := make(chan struct{})
	defer close(done)

	go func() {
		ticker := time.NewTicker(currentTimeouts.PingPeriod)
		defer ticker.Stop()

		for {
			select {
			case <-ticker.C:
				deadline := time.Now().Add(currentTimeouts.WriteWait)
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
		conn.SetReadDeadline(time.Now().Add(currentTimeouts.PongWait))
		messageType, message, err := conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				// Log unexpected errors in production
			}
			break
		}

		conn.SetWriteDeadline(time.Now().Add(currentTimeouts.WriteWait))
		if err := conn.WriteMessage(messageType, message); err != nil {
			break
		}
	}
}

package connections

import (
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// TimeoutConfig holds the various timeout settings for WebSocket connections
type TimeoutConfig struct {
	PongWait   time.Duration
	PingPeriod time.Duration
	WriteWait  time.Duration
}

// Manager handles WebSocket connection lifecycle
type Manager struct {
	connections sync.Map
	timeouts    TimeoutConfig
}

// DefaultTimeouts provides sensible default timeout values
var DefaultTimeouts = TimeoutConfig{
	PongWait:   30 * time.Second,
	PingPeriod: 27 * time.Second, // (PongWait * 9) / 10
	WriteWait:  10 * time.Second,
}

// NewManager creates a new connection manager with the specified timeouts
func NewManager(timeouts TimeoutConfig) *Manager {
	return &Manager{
		timeouts: timeouts,
	}
}

// AddConnection registers a new WebSocket connection
func (m *Manager) AddConnection(conn *websocket.Conn) {
	m.connections.Store(conn, struct{}{})
}

// RemoveConnection removes a WebSocket connection
func (m *Manager) RemoveConnection(conn *websocket.Conn) {
	m.connections.Delete(conn)
}

// GetConnectionCount returns the current number of active connections
func (m *Manager) GetConnectionCount() int {
	count := 0
	m.connections.Range(func(key, value interface{}) bool {
		count++
		return true
	})
	return count
}

// HasConnection checks if a specific connection exists
func (m *Manager) HasConnection(conn *websocket.Conn) bool {
	_, exists := m.connections.Load(conn)
	return exists
}

// GetTimeouts returns the current timeout configuration
func (m *Manager) GetTimeouts() TimeoutConfig {
	return m.timeouts
}

// SetTimeouts updates the timeout configuration
func (m *Manager) SetTimeouts(timeouts TimeoutConfig) {
	m.timeouts = timeouts
}

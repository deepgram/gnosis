package connections

import (
	"context"
	"runtime"
	"sync"
	"testing"
	"time"

	"github.com/gorilla/websocket"
)

func TestManager(t *testing.T) {
	// Create a context with timeout for the entire test
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// Add cleanup function that will run after each test
	t.Cleanup(func() {
		cancel()
		// Give any goroutines a chance to clean up
		time.Sleep(100 * time.Millisecond)
	})

	t.Run("basic add and remove connection", func(t *testing.T) {
		manager := NewManager(DefaultTimeouts)

		conn := &websocket.Conn{}

		// Add connection
		manager.AddConnection(conn)
		if !manager.HasConnection(conn) {
			t.Error("Connection not found after adding")
		}

		// Remove connection
		manager.RemoveConnection(conn)
		if manager.HasConnection(conn) {
			t.Error("Connection still exists after removal")
		}
	})

	t.Run("concurrent connection operations", func(t *testing.T) {
		manager := NewManager(DefaultTimeouts)
		concurrentOps := 100
		var wg sync.WaitGroup
		wg.Add(concurrentOps)

		// Create a done channel for cleanup
		done := make(chan struct{})
		defer close(done)

		connections := make([]*websocket.Conn, concurrentOps)
		for i := 0; i < concurrentOps; i++ {
			connections[i] = &websocket.Conn{}
		}

		for i := 0; i < concurrentOps; i++ {
			go func(conn *websocket.Conn) {
				defer wg.Done()
				select {
				case <-ctx.Done():
					return
				default:
					manager.AddConnection(conn)
				}
			}(connections[i])
		}

		// Wait with timeout
		waitCh := make(chan struct{})
		go func() {
			wg.Wait()
			close(waitCh)
		}()

		select {
		case <-ctx.Done():
			t.Fatal("Test timed out")
		case <-waitCh:
			// Continue with test
		}

		// Clean up
		for _, conn := range connections {
			manager.RemoveConnection(conn)
		}
	})

	t.Run("memory leak check", func(t *testing.T) {
		manager := NewManager(DefaultTimeouts)
		iterations := 1000

		var m1, m2 runtime.MemStats
		runtime.GC()
		runtime.ReadMemStats(&m1)

		for i := 0; i < iterations; i++ {
			conn := &websocket.Conn{}
			manager.AddConnection(conn)
			manager.RemoveConnection(conn)
		}

		runtime.GC()
		time.Sleep(100 * time.Millisecond) // Allow time for GC to complete
		runtime.ReadMemStats(&m2)

		// Handle both positive and negative growth
		var memoryGrowth int64
		if m2.HeapAlloc >= m1.HeapAlloc {
			memoryGrowth = int64(m2.HeapAlloc - m1.HeapAlloc)
		} else {
			memoryGrowth = -int64(m1.HeapAlloc - m2.HeapAlloc)
		}

		// Set a reasonable threshold (e.g., 1KB per iteration)
		maxAcceptableGrowth := int64(iterations * 1024) // 1KB per iteration
		if memoryGrowth > maxAcceptableGrowth {
			t.Errorf("Possible memory leak detected: memory growth of %d bytes exceeds threshold of %d bytes",
				memoryGrowth, maxAcceptableGrowth)
		}

		select {
		case <-ctx.Done():
			t.Fatal("Memory leak test timed out")
		default:
			// Continue with test
		}
	})

	t.Run("timeout configuration", func(t *testing.T) {
		customTimeouts := TimeoutConfig{
			PongWait:   1 * time.Minute,
			PingPeriod: 54 * time.Second,
			WriteWait:  20 * time.Second,
		}

		manager := NewManager(customTimeouts)
		timeouts := manager.GetTimeouts()

		if timeouts != customTimeouts {
			t.Error("Timeout configuration not set correctly")
		}

		// Test timeout update
		newTimeouts := TimeoutConfig{
			PongWait:   2 * time.Minute,
			PingPeriod: 108 * time.Second,
			WriteWait:  30 * time.Second,
		}
		manager.SetTimeouts(newTimeouts)

		if manager.GetTimeouts() != newTimeouts {
			t.Error("Timeout configuration not updated correctly")
		}
	})
}

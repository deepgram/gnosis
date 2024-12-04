package proxy

import (
	"github.com/deepgram/gnosis/internal/config"
	"github.com/deepgram/gnosis/internal/infrastructure/deepgram"

	"fmt"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"github.com/rs/zerolog/log"
)

type MessageProcessor func(messageType int, message []byte, srcConn *websocket.Conn) (*[]byte, error)

type Service struct {
	mu              sync.RWMutex
	deepgramService *deepgram.Service
	deepgramConn    *websocket.Conn
	errChan         chan error
	done            chan struct{}
	processors      []MessageProcessor
	isClosing       bool
}

const (
	maxReconnectAttempts = 3
	reconnectDelay       = 2 * time.Second
)

func NewAgentService(deepgramService *deepgram.Service) *Service {
	token := config.GetDeepgramAPIKey()

	if token == "" {
		log.Fatal().Msg("Deepgram API key not configured - service will be unavailable")
	}

	log.Info().Msg("Deepgram service initialized successfully")

	return &Service{
		deepgramService: deepgramService,
		errChan:         make(chan error, 1),
		done:            make(chan struct{}),
		isClosing:       false,
	}
}

func (s *Service) ConnectServer(path string) error {
	var err error

	s.mu.Lock()
	defer s.mu.Unlock()

	// Try to connect with retries
	for attempt := 1; attempt <= maxReconnectAttempts; attempt++ {
		s.deepgramConn, err = s.deepgramService.ConnectSocket(path)
		if err == nil {
			return nil
		}

		log.Warn().
			Int("attempt", attempt).
			Int("max_attempts", maxReconnectAttempts).
			Err(err).
			Msg("Failed to connect to Deepgram server, retrying...")

		if attempt < maxReconnectAttempts {
			time.Sleep(reconnectDelay)
		}
	}

	return fmt.Errorf("failed to connect after %d attempts: %w", maxReconnectAttempts, err)
}

func (s *Service) GetDeepgramService() *deepgram.Service {
	return s.deepgramService
}

func (s *Service) StartProxy(clientConn *websocket.Conn, processors ...MessageProcessor) {
	s.mu.Lock()
	deepgramConn := s.deepgramConn
	s.mu.Unlock()

	s.processors = processors
	go s.proxyMessages(clientConn, deepgramConn, "inbound")
	go s.proxyMessages(deepgramConn, clientConn, "outbound")
}

func (s *Service) proxyMessages(srcConn, dstConn *websocket.Conn, direction string) {
	for {
		select {
		case <-s.done:
			return
		default:
			messageType, message, err := srcConn.ReadMessage()
			if err != nil {
				if !websocket.IsCloseError(err, websocket.CloseNormalClosure) {
					log.Error().Str("direction", direction).Err(err).Msg("Failed to read message")
				}
				s.sendError(err)
				return
			}

			processed, err := s.processMessage(messageType, message, srcConn)
			if err != nil {
				log.Error().Err(err).Msg("Failed to process message")
				s.sendError(err)
				return
			}

			if processed != nil {
				if err := s.sendMessage(dstConn, messageType, *processed); err != nil {
					log.Error().Err(err).Msg("Failed to write message")
					s.sendError(err)
					return
				}
			}

			log.Debug().
				Str("direction", direction).
				Int("message_type", messageType).
				Interface("message", processed).
				Msg("Forwarding WebSocket message")
		}
	}
}

func (s *Service) processMessage(messageType int, message []byte, srcConn *websocket.Conn) (*[]byte, error) {
	s.mu.RLock()
	processors := s.processors
	s.mu.RUnlock()

	processed := &message
	for _, processor := range processors {
		var err error
		processed, err = processor(messageType, *processed, srcConn)
		if err != nil {
			return nil, err
		}
	}
	return processed, nil
}

func (s *Service) sendMessage(dst *websocket.Conn, messageType int, msg []byte) error {
	if err := dst.WriteMessage(messageType, msg); err != nil {
		log.Error().Err(err).Msg("Failed to write message")
		s.errChan <- err
		return err
	}

	return nil
}

func (s *Service) Close() {
	s.mu.Lock()
	if s.isClosing {
		s.mu.Unlock()
		return
	}
	s.isClosing = true
	if s.deepgramConn != nil {
		s.deepgramConn.Close()
		s.deepgramConn = nil
	}
	s.mu.Unlock()

	close(s.done)
	close(s.errChan)
}

func (s *Service) sendError(err error) {
	select {
	case s.errChan <- err:
		// Error sent successfully
	case <-s.done:
		// Service is shutting down, ignore the error
	default:
		// Channel is full, log the error instead
		log.Error().Err(err).Msg("Error channel full, logging instead")
	}
}

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

// MessageProcessor will match the signature of a websocket message and run any custom logic required.
// It returns true if it was skipped, false if it was processed or errored.
type MessageProcessor func(messageType int, message []byte, srcConn *websocket.Conn) (bool, *[]byte, error)

type Service struct {
	mu              sync.RWMutex
	deepgramService *deepgram.Service
	deepgramConn    *websocket.Conn
	errChan         *chan error
	done            *chan struct{}
	processors      []MessageProcessor
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
	}
}

func (s *Service) ConnectServer(path string, done chan struct{}, errChan chan error) {
	// Set the done and errChan channels
	s.done = &done
	s.errChan = &errChan

	// Lock the mutex
	s.mu.Lock()
	defer s.mu.Unlock()

	var err error

	log.Trace().Str("path", path).Msg("Attempting to connect to upstream server")

	// Try to connect with retries
	for attempt := 1; attempt <= maxReconnectAttempts; attempt++ {
		log.Debug().Int("attempt", attempt).Str("path", path).Msg("Attempting connection to upstream server")

		s.deepgramConn, err = s.deepgramService.ConnectSocket(path, done, errChan)
		if err != nil {
			if attempt >= maxReconnectAttempts {
				s.sendError(fmt.Errorf("failed to connect after %d attempts: %w", maxReconnectAttempts, err))
				return
			}

			log.Warn().
				Int("attempt", attempt).
				Int("max_attempts", maxReconnectAttempts).
				Err(err).
				Msg("Failed to connect to upstream server, retrying...")

			time.Sleep(reconnectDelay)
			continue
		}

		// Connection successful
		log.Info().Str("path", path).Msg("Successfully connected to upstream server")
		return
	}
}

func (s *Service) GetDeepgramService() *deepgram.Service {
	return s.deepgramService
}

func (s *Service) StartProxy(clientConn *websocket.Conn, processors ...MessageProcessor) {
	s.mu.Lock()
	defer s.mu.Unlock()

	deepgramConn := s.deepgramConn
	if deepgramConn == nil {
		s.sendError(fmt.Errorf("cannot start proxy: Deepgram connection is nil"))
		return
	}

	// Initialize processors slice if provided
	if len(processors) > 0 {
		s.processors = make([]MessageProcessor, len(processors))
		copy(s.processors, processors)
	} else {
		s.processors = make([]MessageProcessor, 0)
	}

	log.Info().Str("client_remote_addr", clientConn.RemoteAddr().String()).Str("deepgram_remote_addr", deepgramConn.RemoteAddr().String()).Int("processor_count", len(s.processors)).Msg("Starting proxy with verified connections")

	go s.proxyMessages(clientConn, deepgramConn, "inbound")
	go s.proxyMessages(deepgramConn, clientConn, "outbound")

	<-*s.done
}

func (s *Service) proxyMessages(srcConn, dstConn *websocket.Conn, direction string) {
	log.Info().
		Str("direction", direction).
		Msg("Starting proxy message handler")

	for {
		select {
		case <-*s.done:
			log.Info().Str("direction", direction).Msg("Proxy message handler stopped")
			return
		default:
			messageType, message, err := srcConn.ReadMessage()
			if err != nil {
				closingNormally := websocket.IsCloseError(err, websocket.CloseNormalClosure)
				if closingNormally {
					log.Info().Str("direction", direction).Msg("Proxy message handler stopped normally")
					return
				}
				s.sendError(fmt.Errorf("failed to read message: %w", err))
			}

			var messageToSend *[]byte

			// Only process text messages, pass through all others
			if messageType == websocket.TextMessage {
				// Process the message by running it through all registered processors
				messageToSend = s.processMessage(messageType, message, srcConn)
			} else {
				messageToSend = &message
			}

			// Whether the message was skipped or not, if the processed message is not nil, send it
			if messageToSend != nil {
				s.sendMessage(dstConn, messageType, *messageToSend)
				// Don't return here - continue proxying messages
			}
		}
	}
}

func (s *Service) processMessage(messageType int, message []byte, srcConn *websocket.Conn) *[]byte {
	s.mu.RLock()
	defer s.mu.RUnlock()

	// log.Trace().Interface("message", message).Int("message_type", messageType).Msg("Processing message")

	// If no processors are registered, return the original message
	if len(s.processors) == 0 {
		log.Debug().Msg("No message processors registered, passing through original message")
		return &message
	}

	for _, processor := range s.processors {
		skipped, processedMessage, err := processor(messageType, message, srcConn)

		if skipped {
			log.Debug().Msg("Processor skipped message")
			continue
		}

		if err != nil {
			s.sendError(err)
			return nil
		}

		return processedMessage
	}

	return &message
}

func (s *Service) sendMessage(dst *websocket.Conn, messageType int, msg []byte) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if err := dst.WriteMessage(messageType, msg); err != nil {
		s.sendError(err)
	}
}

func (s *Service) sendError(err error) {
	// Log the error
	log.Error().Err(err).Msg(err.Error())

	select {
	case *s.errChan <- err:
		// Error sent successfully
	case <-*s.done:
		// Service is shutting down, ignore the error
	default:
		// Channel is full, log the error instead
		log.Error().Err(fmt.Errorf("error channel full, logging instead: %w", err)).Msg("Error channel full, logging instead")
	}
}

// Close will close the Deepgram connection and signal the shutdown of the proxy
func (s *Service) Close() {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.deepgramConn != nil {
		s.deepgramConn.Close()
	}
}

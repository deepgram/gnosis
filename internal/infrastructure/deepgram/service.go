package deepgram

import (
	"fmt"
	"io"
	"net/http"
	"net/url"
	"sync"

	"github.com/deepgram/gnosis/internal/config"
	"github.com/gorilla/websocket"
	"github.com/rs/zerolog/log"
)

type Service struct {
	mu        sync.RWMutex
	Client    *http.Client `json:"client"`
	RestURL   string       `json:"rest_url"`
	SocketURL string       `json:"socket_url"`
	Headers   http.Header  `json:"headers"`
}

func NewService() *Service {
	token := config.GetDeepgramAPIKey()

	if token == "" {
		log.Fatal().Msg("Deepgram API key not configured - service will be unavailable")
	}

	headers := http.Header{}
	headers.Add("Authorization", "token "+token)

	s := &Service{
		mu:        sync.RWMutex{},
		Client:    &http.Client{},
		RestURL:   "https://api.deepgram.com",
		SocketURL: "wss://api.deepgram.com",
		Headers:   headers,
	}

	log.Info().
		Interface("deepgram_service", s).
		Msg("Deepgram service initialized successfully")

	return s
}

// SetRestURL sets the REST URL for the service
func (s *Service) SetRestURL(url string) *Service {
	s.RestURL = url
	return s
}

// SetSocketURL sets the WebSocket URL for the service
func (s *Service) SetSocketURL(url string) *Service {
	s.SocketURL = url
	return s
}

// MakeRequest makes a request to the Deepgram REST API
func (s *Service) MakeRequest(method, path string, body io.Reader) (*http.Response, error) {
	req, err := http.NewRequest(method, s.RestURL+path, body)
	if err != nil {
		return nil, err
	}

	req.Header = s.Headers

	return s.Client.Do(req)
}

// ConnectSocket connects to the Deepgram WebSocket API
func (s *Service) ConnectSocket(path string) (*websocket.Conn, error) {
	errChan := make(chan error, 2)

	// error if trying to connect without url
	if s.SocketURL == "" {
		return nil, fmt.Errorf("socket URL is required before connecting to Deepgram agent server")
	}

	// error if trying to connect without headers
	if s.Headers == nil {
		return nil, fmt.Errorf("headers are required before connecting to Deepgram agent server")
	}

	u, err := url.Parse(s.SocketURL + path)
	if err != nil {
		log.Error().Err(err).Msg("Failed to parse Deepgram agent server URL")
		errChan <- err
		return nil, err
	}

	conn, _, err := websocket.DefaultDialer.Dial(u.String(), s.Headers)
	if err != nil {
		log.Error().Err(err).Msg("Failed to connect to Deepgram agent server")
		return nil, err
	}

	err = <-errChan
	if err != nil {
		if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
			log.Error().Err(err).Msg("Unexpected WebSocket closure")
		} else {
			log.Info().Err(err).Msg("WebSocket connection closed gracefully")
		}
	}

	return conn, nil
}

package config

import (
	"fmt"

	"github.com/rs/zerolog/log"
)

func GetDeepgramAPIKey() string {
	key := GetEnvOrDefault("DEEPGRAM_API_KEY", "")
	if key == "" {
		log.Error().Msg("DEEPGRAM_API_KEY environment variable is not set")
		return ""
	}

	log.Debug().
		Str("key_length", fmt.Sprintf("%d", len(key))).
		Msg("Deepgram API key loaded successfully")

	return key
}

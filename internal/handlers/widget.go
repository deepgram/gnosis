package handlers

import (
	"net/http"

	"github.com/deepgram/gnosis/internal/logger"
)

func HandleWidgetJS(w http.ResponseWriter, r *http.Request) {
	logger.Debug(logger.HANDLER, "Serving widget.js request from %s", r.RemoteAddr)

	// Set appropriate headers
	w.Header().Set("Content-Type", "application/javascript")
	w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")
	w.Header().Set("Pragma", "no-cache")
	w.Header().Set("Expires", "0")

	// For now, return a simple console.log
	// This will be replaced with actual widget code later
	js := `
		console.log("Deepgram Gnosis Widget loaded");
		window.GNOSIS_WIDGET_ID = "gnosis-" + Math.random().toString(36).substring(2);
	`

	w.Write([]byte(js))
}

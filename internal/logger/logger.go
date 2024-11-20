package logger

import (
	"log"
	"os"
	"strings"
)

type LogLevel int

const (
	ERROR LogLevel = iota
	WARN
	INFO
	DEBUG
)

var currentLevel = getLogLevel()

func getLogLevel() LogLevel {
	level := strings.ToUpper(os.Getenv("LOG_LEVEL"))
	switch level {
	case "DEBUG":
		return DEBUG
	case "INFO":
		return INFO
	case "WARN":
		return WARN
	case "ERROR":
		return ERROR
	default:
		return INFO // Default level
	}
}

func Debug(format string, v ...interface{}) {
	if currentLevel >= DEBUG {
		log.Printf("[DEBUG] "+format, v...)
	}
}

func Info(format string, v ...interface{}) {
	if currentLevel >= INFO {
		log.Printf("[INFO] "+format, v...)
	}
}

func Warn(format string, v ...interface{}) {
	if currentLevel >= WARN {
		log.Printf("[WARN] "+format, v...)
	}
}

func Error(format string, v ...interface{}) {
	if currentLevel >= ERROR {
		log.New(os.Stderr, "", log.LstdFlags).Printf("[ERROR] "+format, v...)
	}
}

func Fatal(format string, v ...interface{}) {
	if currentLevel >= ERROR {
		log.New(os.Stderr, "", log.LstdFlags).Printf("[FATAL] "+format, v...)
	}
}

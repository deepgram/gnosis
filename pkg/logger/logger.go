package logger

import (
	"fmt"
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

const (
	APP        = "APP"
	CHAT       = "CHAT"
	CONFIG     = "CONFIG"
	HANDLER    = "HANDLER"
	MIDDLEWARE = "MIDDLEWARE"
	OAUTH      = "OAUTH"
	REDIS      = "REDIS"
	SERVICE    = "SERVICE"
	TOOLS      = "TOOLS"
)

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
		return INFO
	}
}

func formatMessage(level, namespace, format string, v ...interface{}) string {
	msg := fmt.Sprintf(format, v...)
	return fmt.Sprintf("[%s] [%s] %s", level, namespace, msg)
}

func Debug(namespace, format string, v ...interface{}) {
	if currentLevel >= DEBUG {
		log.Print(formatMessage("DEBUG", namespace, format, v...))
	}
}

func Info(namespace, format string, v ...interface{}) {
	if currentLevel >= INFO {
		log.Print(formatMessage("INFO", namespace, format, v...))
	}
}

func Warn(namespace, format string, v ...interface{}) {
	if currentLevel >= WARN {
		log.Print(formatMessage("WARN", namespace, format, v...))
	}
}

func Error(namespace, format string, v ...interface{}) {
	if currentLevel >= ERROR {
		log.New(os.Stderr, "", log.LstdFlags).Print(formatMessage("ERROR", namespace, format, v...))
	}
}

func Fatal(namespace, format string, v ...interface{}) {
	if currentLevel >= ERROR {
		log.New(os.Stderr, "", log.LstdFlags).Print(formatMessage("FATAL", namespace, format, v...))
	}
}

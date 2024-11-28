package logger

import (
	"bytes"
	"io"
	"log"
	"os"
	"strings"
	"testing"
)

func TestGetLogLevel(t *testing.T) {
	tests := []struct {
		name     string
		envLevel string
		want     LogLevel
	}{
		{"Debug level", "DEBUG", DEBUG},
		{"Info level", "INFO", INFO},
		{"Warn level", "WARN", WARN},
		{"Error level", "ERROR", ERROR},
		{"Empty defaults to Info", "", INFO},
		{"Invalid defaults to Info", "INVALID", INFO},
		{"Case insensitive", "debug", DEBUG},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			os.Setenv("LOG_LEVEL", tt.envLevel)
			defer os.Unsetenv("LOG_LEVEL")

			if got := getLogLevel(); got != tt.want {
				t.Errorf("getLogLevel() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestFormatMessage(t *testing.T) {
	tests := []struct {
		name      string
		level     string
		namespace string
		format    string
		args      []interface{}
		want      string
	}{
		{
			name:      "Simple message",
			level:     "INFO",
			namespace: "TEST",
			format:    "Hello",
			args:      nil,
			want:      "[INFO] [TEST] Hello",
		},
		{
			name:      "Message with args",
			level:     "DEBUG",
			namespace: "APP",
			format:    "Count: %d",
			args:      []interface{}{42},
			want:      "[DEBUG] [APP] Count: 42",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := formatMessage(tt.level, tt.namespace, tt.format, tt.args...)
			if got != tt.want {
				t.Errorf("formatMessage() = %v, want %v", got, tt.want)
			}
		})
	}
}

func captureOutput(f func()) string {
	oldStdout := os.Stdout
	oldStderr := os.Stderr
	rOut, wOut, _ := os.Pipe()
	rErr, wErr, _ := os.Pipe()

	os.Stdout = wOut
	os.Stderr = wErr
	log.SetOutput(wOut)

	f()

	log.SetOutput(oldStdout)
	os.Stdout = oldStdout
	os.Stderr = oldStderr

	wOut.Close()
	wErr.Close()

	var stdoutBuf, stderrBuf bytes.Buffer
	if _, err := io.Copy(&stdoutBuf, rOut); err != nil {
		log.Printf("Failed to copy stdout: %v", err)
	}
	if _, err := io.Copy(&stderrBuf, rErr); err != nil {
		log.Printf("Failed to copy stderr: %v", err)
	}

	return stdoutBuf.String() + stderrBuf.String()
}

func TestLogLevels(t *testing.T) {
	tests := []struct {
		name      string
		setLevel  string
		logFunc   func(string, string, ...interface{})
		namespace string
		message   string
		shouldLog bool
		contains  string
	}{
		{
			name:      "Debug logs when Debug",
			setLevel:  "DEBUG",
			logFunc:   Debug,
			namespace: "TEST",
			message:   "debug message",
			shouldLog: true,
			contains:  "[DEBUG] [TEST] debug message",
		},
		{
			name:      "Debug doesn't log when Info",
			setLevel:  "INFO",
			logFunc:   Debug,
			namespace: "TEST",
			message:   "debug message",
			shouldLog: false,
			contains:  "",
		},
		{
			name:      "Info logs when Info",
			setLevel:  "INFO",
			logFunc:   Info,
			namespace: "TEST",
			message:   "info message",
			shouldLog: true,
			contains:  "[INFO] [TEST] info message",
		},
		{
			name:      "Info doesn't log when Error",
			setLevel:  "ERROR",
			logFunc:   Info,
			namespace: "TEST",
			message:   "info message",
			shouldLog: false,
			contains:  "",
		},
		{
			name:      "Error always logs",
			setLevel:  "ERROR",
			logFunc:   Error,
			namespace: "TEST",
			message:   "error message",
			shouldLog: true,
			contains:  "[ERROR] [TEST] error message",
		},
		{
			name:      "Error logs when Debug",
			setLevel:  "DEBUG",
			logFunc:   Error,
			namespace: "TEST",
			message:   "error message",
			shouldLog: true,
			contains:  "[ERROR] [TEST] error message",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			os.Setenv("LOG_LEVEL", tt.setLevel)
			defer os.Unsetenv("LOG_LEVEL")
			currentLevel = getLogLevel()

			output := captureOutput(func() {
				tt.logFunc(tt.namespace, tt.message)
			})

			output = strings.TrimSpace(output)
			hasOutput := output != ""
			if hasOutput != tt.shouldLog {
				t.Errorf("Expected log output: %v, got output: %q", tt.shouldLog, output)
			}

			if tt.shouldLog && !strings.Contains(output, tt.contains) {
				t.Errorf("Expected output to contain %q, got %q", tt.contains, output)
			}
		})
	}
}

func TestFatal(t *testing.T) {
	output := captureOutput(func() {
		Fatal("TEST", "fatal error")
	})

	output = strings.TrimSpace(output)
	expected := "[FATAL] [TEST] fatal error"
	if !strings.Contains(output, expected) {
		t.Errorf("Fatal() output = %q, want to contain %q", output, expected)
	}
}

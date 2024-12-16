#syntax=docker/dockerfile:1.4

FROM --platform=$BUILDPLATFORM golang:1.22-alpine AS builder
WORKDIR /app
COPY . .
RUN apk add --no-cache upx ca-certificates
RUN GOOS=linux GOARCH=amd64 go build -a -ldflags="-w -s" -o bin/gnosis ./cmd/main.go
RUN upx --best --lzma bin/gnosis

FROM scratch

# Copy SSL certificates from builder
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

LABEL org.opencontainers.image.source="https://github.com/deepgram/gnosis"
LABEL org.opencontainers.image.title="Gnosis - Deepgram AI Support Agent API"
LABEL org.opencontainers.image.description="Gnosis provides secure, managed access to Deepgram's AI Support Agent and knowledge services"
LABEL org.opencontainers.image.version=${VERSION}
LABEL org.opencontainers.image.authors="Luke Oliff <luke.oliff@deepgram.com>"
LABEL org.opencontainers.image.documentation="https://deepgram.github.io/gnosis"
LABEL org.opencontainers.image.licenses="LicenseRef-Proprietary-Deepgram"
LABEL org.opencontainers.image.base.name="gnosis"

ENV LOG_LEVEL=warn

COPY --from=builder /app/bin/gnosis /gnosis
EXPOSE 8080
ENTRYPOINT ["/gnosis"]
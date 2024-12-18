#syntax=docker/dockerfile:1.4

FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY . .
RUN apk add --no-cache upx ca-certificates
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -a \
    -o bin/gnosis ./cmd/main.go
RUN upx --best --lzma bin/gnosis

FROM scratch

# Copy SSL certificates from builder
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

LABEL org.opencontainers.image.source="https://github.com/deepgram/gnosis"
LABEL org.opencontainers.image.title="Gnosis - Intelligent Knowledge Gateway"
LABEL org.opencontainers.image.description="A unified API gateway that enhances AI interactions with contextual knowledge from diverse sources, providing intelligent responses across multiple communication modalities"
LABEL org.opencontainers.image.version=${VERSION}
LABEL org.opencontainers.image.authors="Luke Oliff <luke.oliff@deepgram.com>"
LABEL org.opencontainers.image.documentation="https://deepgram.github.io/gnosis"
LABEL org.opencontainers.image.licenses="LicenseRef-Proprietary-Deepgram"
LABEL org.opencontainers.image.base.name="gnosis"

ENV LOG_LEVEL=warn

COPY --from=builder /app/bin/gnosis /gnosis
EXPOSE 8080
ENTRYPOINT ["/gnosis"]
#syntax=docker/dockerfile:1.4

FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=warn

# Labels
LABEL org.opencontainers.image.source="https://github.com/deepgram/gnosis"
LABEL org.opencontainers.image.title="Gnosis - Intelligent Knowledge Gateway"
LABEL org.opencontainers.image.description="A unified API gateway that enhances AI interactions with contextual knowledge from diverse sources, providing intelligent responses across multiple communication modalities"
LABEL org.opencontainers.image.version=${VERSION}
LABEL org.opencontainers.image.authors="Luke Oliff <luke.oliff@deepgram.com>"
LABEL org.opencontainers.image.documentation="https://deepgram.github.io/gnosis"
LABEL org.opencontainers.image.licenses="LicenseRef-Proprietary-Deepgram"
LABEL org.opencontainers.image.base.name="gnosis"

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "main.py"]
# Gnosis

_(ˈnəʊ.sɪs)_  
_noun_

1. Knowledge of spiritual mysteries.
   - _Example:_ "The philosopher dedicated his life to the pursuit of gnosis."

**Origin:**  
Late 16th century: from Greek _gnōsis_, meaning ‘knowledge’, from _gignōskein_, meaning ‘to know’.

---

Gnosis is a lightweight API gateway that provides secure, managed access to various knowledge and assistance services. It acts as a unified interface for both internal and external clients, handling authentication, request routing, and response formatting.

## Features

- **Authentication & Security**: JWT-based auth, anonymous sessions
- **API Integration**: OpenAI, Kapa.ai, Algolia, GitHub
- **Performance**: Lightweight stateless design, concurrent request handling
- **Development**: Go best practices, environment-based config
- **Monitoring**: Structured logging with configurable levels
- **Standards**: RESTful API, OpenAPI 3.0 spec, JSON responses, Bearer scheme

## Prerequisites

- Go 1.21 or higher
- Make (optional, for using Makefile commands)

## Installation

Clone the repository:

```sh
git clone https://github.com/deepgram/gnosis.git
cd gnosis
```

Install dependencies:

```sh
go mod download
```

## Configuration

Create a `.env` file in the project root:

```sh
# JWT Secret (required)
JWT_SECRET=your-256-bit-secret

# OpenAI API Key (required)
OPENAI_KEY=your-openai-key

# Algolia Credentials (required)
ALGOLIA_APP_ID=your_algolia_app_id
ALGOLIA_API_KEY=your_algolia_api_key
ALGOLIA_INDEX_NAME=your_index_name

# GitHub Token (required)
GITHUB_TOKEN=your_github_token

# Kapa Credentials (required)
KAPA_INTEGRATION_ID=kapa-integration-id
KAPA_PROJECT_ID=kapa-project-id
KAPA_API_KEY=kapa-api-key

# Client Configuration (required - see below)

# Session Cookie Name
SESSION_COOKIE_NAME=gnosis_session

# Optional
## Log Level (defaults to INFO)
LOG_LEVEL=INFO # DEBUG|INFO|WARN|ERROR

## Redis Configuration (optional - falls back to in-memory session store)
REDIS_URL=
REDIS_PASSWORD=
```

## Client Configuration

Gnosis supports dynamic client configuration through environment variables. Each client requires a specific set of environment variables following this pattern:

```sh
GNOSIS_<CLIENT_TYPE>_CLIENT_ID=your_client_id
GNOSIS_<CLIENT_TYPE>_CLIENT_SECRET=your_client_secret
GNOSIS_<CLIENT_TYPE>_NO_SECRET=true # Optional, defaults to false
GNOSIS_<CLIENT_TYPE>_ALLOWED_URLS=https://example.com,https://app.example.com # Optional, defaults to empty
GNOSIS_<CLIENT_TYPE>_SCOPES=scope1,scope2 # Optional, defaults to empty
```

### Example

```sh
GNOSIS_SLACK_CLIENT_ID=slack-client-id
GNOSIS_SLACK_CLIENT_SECRET=slack-client-secret
GNOSIS_SLACK_SCOPES=scope1,scope2

GNOSIS_WIDGET_CLIENT_ID=widget-client-id
GNOSIS_WIDGET_NO_SECRET=true
GNOSIS_WIDGET_ALLOWED_URLS=https://example.com,https://app.example.com
GNOSIS_WIDGET_SCOPES=scope1,scope2
```

## Usage

Start the development server:

```sh
make dev
```

Build and run the binary:

```sh
# Build the binary
make build

# Run the binary
./bin/gnosis
```

Build and run using Docker:

```sh
# Build the Docker image
make build-image

# Run the Docker container
make run-image
```

The service will start on port 8080 by default.

## API Documentation

See [docs/openapi.yaml](./docs/openapi.yaml) for detailed API documentation.

Key endpoints:

- `POST /v1/oauth/token`: Authentication endpoint
- `POST /v1/chat/completions`: Chat completion endpoint

## Development

```sh
# Run tests
make test

# Run linter
make lint

# Clean build artifacts
make clean
```

## Deployment

Build the Docker image

```sh
make build-image
```

Login to Quay

```sh
docker login quay.io
```

Or if you use 1Password you can reference your credentials from the `Quay` item in a `Personal` vault.

```sh
# e.g. op://Personal/Quay/password
echo $(op read "op://<VAULT>/<ITEM>/<PASSWORD>") | \
   docker login quay.io --username=$(op read "op://<VAULT>/<ITEM>/<PASSWORD>") --password-stdin
```

## Version the image

```sh
export VERSION=1.0.0
docker image tag gnosis:latest quay.io/deepgram/gnosis:$VERSION
make tag-image
```

## Push the Docker image to Quay

```sh
docker push quay.io/deepgram/gnosis:$VERSION
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary software owned by Deepgram. All rights reserved.

## Security

For security concerns, please email <security@deepgram.com>

## Support

For support questions, please email <devrel@deepgram.com>

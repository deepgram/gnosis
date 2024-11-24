# Gnosis

Gnosis is a lightweight API gateway that provides secure, managed access to various knowledge and assistance services. It acts as a unified interface for both internal and external clients, handling authentication, request routing, and response formatting.

## Roadmap

### API Enhancements

- [ ] Implement streaming responses for real-time LLM processing feedback
- [x] Allow clients to safely augment system prompts
- [ ] Support custom tool calls alongside Gnosis's built-in ones
- [x] Enable/disable tool calls based on environment configuration
- [ ] Add session cookies for certain special routes

### Widget Integration

- [ ] Serve widget from /widget.js (loaded from disk on runtime)

### Deployment

- [ ] Host inside VPN for access to internal tools API

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

1. Clone the repository:

```sh
git clone https://github.com/deepgram/gnosis.git
cd gnosis
```

2. Install dependencies:

```sh
go mod download
```

## Configuration

Create a `.env` file in the project root:

```sh
# Required
JWT_SECRET=your-256-bit-secret
OPENAI_KEY=your-openai-key

# Optional Services
KAPA_INTEGRATION_ID=kapa-integration-id
KAPA_PROJECT_ID=kapa-project-id
KAPA_API_KEY=kapa-api-key

ALGOLIA_APP_ID=your_algolia_app_id
ALGOLIA_API_KEY=your_algolia_api_key
ALGOLIA_INDEX_NAME=your_index_name

GITHUB_TOKEN=your_github_token

# Client Credentials
GNOSIS_SLACK_CLIENT_ID=your_slack_client_id
GNOSIS_SLACK_CLIENT_SECRET=your_slack_client_secret
GNOSIS_DISCORD_CLIENT_ID=your_discord_client_id
GNOSIS_DISCORD_CLIENT_SECRET=your_discord_client_secret
GNOSIS_WIDGET_CLIENT_ID=your_widget_client_id
GNOSIS_WIDGET_ALLOWED_URLS=https://example.com,https://app.example.com

# Optional
LOG_LEVEL=INFO # DEBUG|INFO|WARN|ERROR
```

## Usage

Start the development server:

```sh
make dev
```

Or build and run the binary:

```sh
make build
./bin/gnosis
```

The service will start on port 8080 by default.

## API Documentation

See [api/openapi.yaml](./api/openapi.yaml) for detailed API documentation.

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

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary software owned by Deepgram. All rights reserved.

## Security

For security concerns, please email security@deepgram.com

## Support

For support questions, please email devrel@deepgram.com

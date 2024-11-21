# Sage

Sage is a lightweight API gateway that provides secure, managed access to various knowledge and assistance services. It acts as a unified interface for both internal and external clients, handling authentication, request routing, and response formatting.

## TODO

- Add support for streaming responses. I'd like to be able to stream back to the client as the LLM is processing the request.
- Add support for tool calls. I'd like to be able to augment (safely) the system prompt and add tool calls to the LLM, with the built-in system prompt and tool calls being unaffected (and filtered from the responses), allowing for the client apps to use their own tool calls on top of the Sage-provided ones.
- Introduce the react app into another part of the directory structure, and have Sage build and serve it as widget.js when requested by the client.
- Add a /v1/sessions/{session_id} endpoint that allows a client with a server session to request a JWT token for a client session without going through the entire OAuth flow - allowing for browser-clients to securely use Sage without exposing any client secrets.

## Features

### Authentication & Security

- Secure JWT-based authentication flow
- Anonymous session support for quick access
- Token refresh mechanism
- Environment-based configuration for sensitive data
- Rate limiting and request validation

### API Integration

- Seamless integration with OpenAI's GPT-4
- Direct connection to Kapa.ai knowledge base
- Extensible architecture for additional AI services
- Structured response formatting
- Comprehensive error handling

### Performance & Reliability

- Lightweight, stateless design
- Concurrent request handling
- Graceful error recovery
- Structured logging with configurable levels
- Request context management

### Development Experience

- Clear project structure following Go best practices
- Comprehensive API documentation using OpenAPI 3.0
- Environment-based configuration
- Docker support for consistent deployments
- Built-in development tools and commands

### Monitoring & Debugging

- Detailed logging with configurable verbosity
- Request tracing capabilities
- Error tracking and reporting
- Performance metrics collection
- Debug endpoints for development

### Standards Compliance

- RESTful API design
- OpenAPI 3.0 specification
- JSON response formatting
- Standard HTTP status codes
- Bearer token authentication

## Prerequisites

- Go 1.21 or higher
- Make (optional, for using Makefile commands)

## Installation

1. Clone the repository:
   `git clone https://github.com/deepgram/codename-sage.git`

2. Navigate to the project directory:
   `cd codename-sage`

3. Install dependencies:
   `go mod download`

## Configuration

Create a .env file in the project root with the following variables:

```env
JWT_SECRET=your-256-bit-secret
OPENAI_KEY=your-openai-key
KAPA_INTEGRATION_ID=your-kapa-integration-id
KAPA_PROJECT_ID=your-kapa-project-id
KAPA_API_KEY=your-kapa-api-key
```

Optional environment variables:

```env
LOG_LEVEL=INFO (DEBUG|INFO|WARN|ERROR)
```

## Usage

Start the development server:

```sh
make dev
```

Or build and run the binary:

```sh
make build
./bin/sage
```

The service will start on port 8080 by default.

## API Endpoints

### POST /oauth/token

Authenticate and receive JWT tokens
Supports anonymous authentication and token refresh

### POST /chat/completions

Send chat completion requests
Requires valid JWT token in Authorization header

See [api/openapi.yaml](./api/openapi.yaml) for detailed API documentation.

## Development

Run tests:

```sh
make test
```

Run linter:

```sh
make lint
```

Build binary:

```sh
make build
```

Clean build artifacts:

```sh
make clean
```

## Project Structure

```text
/cmd
  main.go # Application entry point
/internal
/config # Configuration management
/handlers # HTTP request handlers
/logger # Logging utilities
/services # Business logic
/types # Shared types and interfaces
/api
  openapi.yaml # API documentation
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary software owned by Deepgram. All rights reserved.

See [LICENSE](./LICENSE) for full terms.

## Security

For security concerns, please email security@deepgram.com

## Support

For support questions, please email devrel@deepgram.com

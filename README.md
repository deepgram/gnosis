# Gnosis: Intelligent Knowledge Gateway

_(ˈnəʊ.sɪs)_  
_noun_

1. Knowledge of spiritual mysteries.
   - _Example:_ "The philosopher dedicated his life to the pursuit of gnosis."

**Origin:**  
Late 16th century: from Greek _gnōsis_, meaning 'knowledge', from _gignōskein_, meaning 'to know'.

---

Gnosis is a unified API gateway that enhances AI interactions with contextual knowledge from diverse sources, providing intelligent responses across multiple communication modalities.

## Key Features

- **Multi-Modal Support**: Handle text, voice, and real-time streaming interactions
- **Dynamic Knowledge Integration**: Real-time function calling with contextual knowledge injection
- **Flexible Authentication**: Support for anonymous sessions and authenticated access
- **Source Architecture**: Pluggable knowledge sources with customisable caching strategies
- **API Compatibility**: Drop-in replacement for OpenAI and Voice Agent APIs
- **WebSocket Support**: Real-time bidirectional communication for voice interactions

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
cp sample.env .env
```

## Client Configuration

Gnosis supports dynamic client configuration through environment variables. Each client requires a specific set of environment variables following this pattern:

```sh
GNOSIS_<CLIENT_TYPE>_CLIENT_ID=your_client_id
GNOSIS_<CLIENT_TYPE>_CLIENT_SECRET=your_client_secret

# define the scopes that the client needs
GNOSIS_<CLIENT_TYPE>_SCOPES=scope1,scope2 # Optional, defaults to empty
```

### Example

```sh
# Integrate with Slack
GNOSIS_SLACK_CLIENT_ID=slack-client-id
GNOSIS_SLACK_CLIENT_SECRET=slack-client-secret

# doesn't need agent:write because we won't have a voice agent in Slack yet
GNOSIS_SLACK_SCOPES=chat:write
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

The service will start on port 8080 by default.

## API Documentation

See [docs/openapi.yaml](./docs/openapi.yaml) for detailed API documentation.

Key endpoints:

- `POST /v1/oauth/token`: Authentication endpoint
- `POST /v1/chat/completions`: Chat completion endpoint
- `WSS /v1/agent`: Agent endpoint

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

This deployment process is managed by the Makefile. It assumes that you have created a git tag for the version you want to deploy. It will use this tag to tag the Docker image and push it to Quay.

To deploy Gnosis, follow these steps:

1. Build the Docker image:

```sh
make build-image
```

1. Tag the Docker image:

```sh
make tag-image
```

1. Push the Docker image to Quay:

```sh
make push-image
```

1. Plan the Nomad job:

```sh
make nomad-plan
```

1. Deploy the Nomad job:

```sh
make nomad-deploy
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

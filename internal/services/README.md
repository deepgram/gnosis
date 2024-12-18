# Services Layer

This directory contains the service implementations and domain models for the Gnosis knowledge gateway.

## Structure

```txt
services/
├── chat/
│   ├── implementation.go    # Chat service implementation
│   ├── prompt.go           # System prompt handling
│   └── models/             # Chat-specific domain models
├── tools/
│   ├── service.go          # Knowledge source integration
│   ├── executor.go         # Source execution logic
│   └── models/             # Source-specific domain models
└── README.md
```

## Design Principles

1. **Service-Domain Separation**: Each service directory contains both its implementation and domain models, keeping related code together whilst maintaining logical separation.

2. **Interface Segregation**: Services are defined through interfaces, allowing for multiple implementations and easier testing.

3. **Clean Architecture**: The domain models have no dependencies on infrastructure or external services. All external integrations are handled through the infrastructure layer.

4. **Source Architecture**: Knowledge sources are implemented as pluggable components with standardised interfaces for execution and caching.

## Key Components

### Service Implementation

- Contains the concrete implementation of service interfaces
- Handles coordination between domain logic and infrastructure
- Manages state and concurrency where needed

### Domain Models

- Represents the core business objects and rules
- Contains validation logic and type definitions
- Remains independent of external concerns

### Infrastructure Integration

- External service clients remain in `/internal/infrastructure`
- Services coordinate with infrastructure through well-defined interfaces
- Keeps infrastructure concerns separate from business logic

## Usage Guidelines

1. Keep domain models focused on business rules
2. Handle external dependencies in service implementations
3. Use interfaces to define service contracts
4. Document complex business logic
5. Maintain clear separation between domain and infrastructure code

## Example Service Structure

For a new service named "example":

```txt
services/
└── example/
    ├── service.go          # Main service implementation
    ├── handler.go          # Additional service logic
    └── models/
        ├── types.go        # Domain types
        └── validation.go   # Domain validation rules
```

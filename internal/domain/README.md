# Domain Layer

This directory contains the core business logic and domain models for the Gnosis application.

## Structure

```txt
domain/
├── chat/
│   ├── models/
│   │   ├── message.go    # Chat message and response types
│   │   ├── prompt.go     # System prompt configuration
│   │   └── tool.go       # Tool execution interfaces and types
│   └── service.go        # Chat service interface definitions
└── README.md
```

## Design Principles

1. **Domain-Driven Design**: The domain layer represents the core business logic and rules, independent of external concerns.

2. **Interface Segregation**: Services are defined through interfaces, allowing for multiple implementations and easier testing.

3. **Clean Architecture**: The domain layer has no dependencies on infrastructure or external services.

## Key Components

### Chat Domain

- **Service Interface**: Defines the contract for chat processing operations
- **Repository Interface**: Defines the contract for chat storage operations
- **Models**: Contains all domain-specific types and validation rules

### Tool Execution

Tool execution is modelled as a domain concern but implemented in the services layer. This allows for:

- Clear separation between tool definitions and implementations
- Easy addition of new tools without modifying domain logic
- Consistent error handling across different tool types

## Usage Guidelines

1. Keep the domain layer focused on business logic
2. Avoid adding external dependencies
3. Use interfaces to define contracts
4. Keep models simple and focused
5. Document any complex business rules

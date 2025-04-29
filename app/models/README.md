# Pydantic Models

This directory contains all the Pydantic models used throughout the Gnosis application for data validation, serialization, and documentation.

## Overview

Pydantic is a data validation and settings management library. We use it to:

1. Define and validate the structure of data
2. Parse and validate incoming request payloads
3. Serialize data for API responses
4. Generate OpenAPI documentation

## Model Organization

The models are organized into several modules:

- `chat.py`: Models for the OpenAI Chat Completions API
- `agent.py`: Models for the Deepgram Voice Agent API
- `tools.py`: Models for tool definitions and responses

## Usage Guidelines

### Validating Data

Use Pydantic models to validate data at the boundaries of your application:

```python
from app.models.chat import ChatCompletionRequest

# Incoming data from an HTTP request
request_data = {...}

# Parse and validate
try:
    validated_request = ChatCompletionRequest(**request_data)
    # The data is now valid and you can access it via validated_request
except ValidationError as e:
    # Handle validation error
```

### Creating New Models

When creating new models, follow these guidelines:

1. Add type annotations for all fields
2. Use appropriate Pydantic types and validators
3. Add docstrings for the class and complex fields
4. Use field validators when necessary

Example:

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional

class MyModel(BaseModel):
    """Description of my model."""
    id: str
    name: str
    count: Optional[int] = Field(default=0, ge=0)
    
    @field_validator('name')
    @classmethod
    def check_name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v
```

### Extending Models

When you need to extend existing models, prefer composition over inheritance when possible:

```python
class ExtendedModel(BaseModel):
    """An extended model that includes the base model."""
    base: BaseModel
    additional_field: str
``` 
import json
import pytest
from app.models.chat import ChatCompletionRequest


def test_parse_standard_chat_completion_request():
    """Test that a standard chat completion request can be parsed."""
    request_json = """
    {
      "model": "gpt-4.1",
      "messages": [
        {
          "role": "user",
          "content": "What is the weather like in Boston today?"
        }
      ]
    }
    """

    # Parse the JSON string into a dict
    request_data = json.loads(request_json)

    # Create a model instance from the dict
    model = ChatCompletionRequest(**request_data)

    # Verify the basic properties
    assert model.model == "gpt-4.1"
    assert len(model.messages) == 1
    assert model.messages[0].role == "user"
    assert model.messages[0].content == "What is the weather like in Boston today?"


def test_parse_request_with_tools():
    """Test that a request with tools can be parsed."""
    request_json = """
    {
      "model": "gpt-4.1",
      "messages": [
        {
          "role": "user",
          "content": "What is the weather like in Boston today?"
        }
      ],
      "tools": [
        {
          "type": "function",
          "function": {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
              "type": "object",
              "properties": {
                "location": {
                  "type": "string",
                  "description": "The city and state, e.g. San Francisco, CA"
                },
                "unit": {
                  "type": "string",
                  "enum": ["celsius", "fahrenheit"]
                }
              },
              "required": ["location"]
            }
          }
        }
      ],
      "tool_choice": "auto"
    }
    """

    # Parse the JSON string into a dict
    request_data = json.loads(request_json)

    # Create a model instance from the dict
    model = ChatCompletionRequest(**request_data)

    # Verify the tools-related properties
    assert model.model == "gpt-4.1"
    assert model.tools is not None
    assert len(model.tools) == 1
    assert model.tools[0].type == "function"
    assert model.tools[0].function.name == "get_current_weather"
    assert model.tool_choice == "auto"


def test_parse_request_with_arbitrary_properties():
    """Test that a request with arbitrary properties can be parsed."""
    request_json = """
    {
      "model": "gpt-4.1",
      "messages": [
        {
          "role": "user",
          "content": "What is the weather like in Boston today?"
        }
      ],
      "tools": [
        {
          "type": "function",
          "function": {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
              "type": "object",
              "properties": {
                "location": {
                  "type": "string",
                  "description": "The city and state, e.g. San Francisco, CA",
                  "example": "Boston, MA",
                  "min_length": 2,
                  "max_length": 100
                },
                "unit": {
                  "type": "string",
                  "enum": ["celsius", "fahrenheit"],
                  "default": "celsius"
                },
                "include_forecast": {
                  "type": "boolean",
                  "description": "Whether to include a forecast"
                }
              },
              "required": ["location"]
            }
          }
        }
      ],
      "tool_choice": "auto",
      "custom_parameter": "value",
      "debug_mode": true,
      "metadata": {
        "user_id": "123456",
        "session_id": "abcdef",
        "tags": ["weather", "location"]
      }
    }
    """

    # Parse the JSON string into a dict
    request_data = json.loads(request_json)

    # Create a model instance from the dict
    model = ChatCompletionRequest(**request_data)

    # Verify the arbitrary properties are included
    model_dict = model.model_dump()
    assert model_dict["custom_parameter"] == "value"
    assert model_dict["debug_mode"] is True
    assert model_dict["metadata"]["user_id"] == "123456"
    assert "include_forecast" in json.dumps(model_dict)


def test_parse_json_string_to_model():
    """Test that any JSON string can be parsed into the model."""

    def validate_json_string(json_string):
        """Helper function to validate a JSON string."""
        try:
            data = json.loads(json_string)
            model = ChatCompletionRequest(**data)
            return True
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            return False

    # Test with various JSON strings
    simple_request = (
        '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "Hello"}]}'
    )
    assert validate_json_string(simple_request)

    complex_request = """
    {
      "model": "gpt-4",
      "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Tell me a story."}
      ],
      "temperature": 0.7,
      "top_p": 0.9,
      "max_tokens": 500,
      "tools": [
        {
          "type": "function",
          "function": {
            "name": "search_database",
            "description": "Search for information",
            "parameters": {
              "type": "object",
              "properties": {
                "query": {"type": "string"},
                "filters": {"type": "object"}
              },
              "required": ["query"]
            }
          }
        }
      ],
      "custom_field": {
        "nested": {
          "deeply": {
            "data": [1, 2, 3]
          }
        }
      }
    }
    """
    assert validate_json_string(complex_request)

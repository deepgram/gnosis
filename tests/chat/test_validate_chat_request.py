"""
Tests for the chat request validation utility.
"""

from typing import cast

from app.utils.validate_chat_request import (
    validate_chat_request,
    validate_chat_request_dict,
)
from app.models.chat import ChatCompletionRequest


def test_validate_valid_chat_request():
    """Test validation of a valid chat request JSON."""
    valid_request = """
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

    is_valid, result = validate_chat_request(valid_request)

    assert is_valid is True
    assert isinstance(result, ChatCompletionRequest)
    model = cast(ChatCompletionRequest, result)
    assert model.model == "gpt-4.1"
    assert model.tools is not None
    assert len(model.tools) == 1
    assert model.tool_choice == "auto"


def test_validate_invalid_json():
    """Test validation of an invalid JSON string."""
    invalid_json = """
    {
      "model": "gpt-4.1",
      "messages": [
        {
          "role": "user",
          "content": "What is the weather like in Boston today?"
        }
      ],
      tools: [  # Missing quotes around property name
        {
          "type": "function",
          "function": {
            "name": "get_current_weather",
            "description": "Get the current weather",
            "parameters": {
              "type": "object",
              "properties": {},
              "required": []
            }
          }
        }
      ]
    }
    """

    is_valid, error_msg = validate_chat_request(invalid_json)

    assert is_valid is False
    assert isinstance(error_msg, str)
    assert "Invalid JSON format" in error_msg


def test_validate_missing_required_fields():
    """Test validation when required fields are missing."""
    # Missing 'model' field
    missing_required = """
    {
      "messages": [
        {
          "role": "user",
          "content": "What is the weather like in Boston today?"
        }
      ]
    }
    """

    is_valid, error_msg = validate_chat_request(missing_required)

    assert is_valid is False
    assert isinstance(error_msg, str)
    assert "Validation error" in error_msg


def test_validate_from_dict():
    """Test validation directly from a dictionary."""
    request_dict = {
        "model": "gpt-4.1",
        "messages": [
            {"role": "user", "content": "What is the weather like in Boston today?"}
        ],
        "custom_field": "custom_value",
        "random_number": 42,
    }

    is_valid, result = validate_chat_request_dict(request_dict)

    assert is_valid is True
    assert isinstance(result, ChatCompletionRequest)
    model = cast(ChatCompletionRequest, result)
    assert model.model == "gpt-4.1"
    model_dict = model.model_dump()
    assert model_dict["custom_field"] == "custom_value"
    assert model_dict["random_number"] == 42


def test_parse_any_valid_request():
    """Test that any reasonably valid request JSON can be parsed."""

    # Function to test validation with arbitrary JSON requests
    def test_request(request_json):
        is_valid, result = validate_chat_request(request_json)
        assert is_valid, f"Failed to validate: {result}"
        assert isinstance(result, ChatCompletionRequest)
        return cast(ChatCompletionRequest, result)

    # Test minimal valid request
    minimal = (
        '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "Hello"}]}'
    )
    test_request(minimal)

    # Test with arbitrary nested fields
    complex_request = """
    {
      "model": "gpt-4",
      "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Tell me a story."}
      ],
      "tools": [
        {
          "type": "function",
          "function": {
            "name": "custom_tool",
            "description": "A custom tool",
            "parameters": {
              "type": "object",
              "properties": {
                "param1": {"type": "string", "custom_field": true},
                "param2": {"type": "number", "custom_validation": {"min": 1, "max": 10}}
              }
            }
          }
        }
      ],
      "custom_settings": {
        "level1": {
          "level2": {
            "level3": [1, 2, {"nested": "value"}]
          }
        }
      }
    }
    """
    result = test_request(complex_request)

    # Verify deep nesting works
    model_dict = result.model_dump()
    assert "custom_settings" in model_dict
    assert (
        model_dict["custom_settings"]["level1"]["level2"]["level3"][2]["nested"]
        == "value"
    )

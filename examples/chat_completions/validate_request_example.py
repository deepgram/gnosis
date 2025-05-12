#!/usr/bin/env python
"""
Example script demonstrating the validation of chat completion requests.
"""
import json
import sys
from typing import cast
from pathlib import Path

# Add project root to path to import app modules
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from app.utils.validate_chat_request import validate_chat_request
from app.models.chat import ChatCompletionRequest


def main():
    """Run the validation example."""
    # Example 1: Standard request with tools
    standard_request = """
    {
      "model": "gpt-4.1",
      "messages": [
        {
          "role": "system",
          "content": "You are a helpful assistant that can provide weather information."
        },
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

    print("Example 1: Standard request with tools")
    is_valid, result = validate_chat_request(standard_request)
    if is_valid:
        print("✅ Valid request")
        # Type check result
        assert isinstance(result, ChatCompletionRequest)
        model = cast(ChatCompletionRequest, result)
        print(f"Model: {model.model}")
        print(f"Number of messages: {len(model.messages)}")
        if model.tools:
            print(f"Number of tools: {len(model.tools)}")
        else:
            print("No tools defined")
        print(f"Tool choice: {model.tool_choice}")
    else:
        print(f"❌ Invalid request: {result}")

    print("\n" + "-" * 50 + "\n")

    # Example 2: Request with custom arbitrary fields
    custom_request = """
    {
      "model": "gpt-4.1",
      "messages": [
        {
          "role": "user",
          "content": "Hello, how are you?"
        }
      ],
      "temperature": 0.7,
      "custom_field": "This is a custom field",
      "metadata": {
        "user_id": "12345",
        "session_data": {
          "session_id": "abcdef",
          "started_at": "2023-07-21T10:30:00Z"
        }
      },
      "debug": true
    }
    """

    print("Example 2: Request with custom arbitrary fields")
    is_valid, result = validate_chat_request(custom_request)
    if is_valid:
        print("✅ Valid request")
        # Type check result
        assert isinstance(result, ChatCompletionRequest)
        model = cast(ChatCompletionRequest, result)
        model_dict = model.model_dump()
        print(f"Model: {model.model}")
        print(f"Custom field: {model_dict.get('custom_field')}")
        print(f"User ID: {model_dict.get('metadata', {}).get('user_id')}")
        print(f"Debug: {model_dict.get('debug')}")
    else:
        print(f"❌ Invalid request: {result}")

    print("\n" + "-" * 50 + "\n")

    # Example 3: Invalid request (missing required field)
    invalid_request = """
    {
      "messages": [
        {
          "role": "user",
          "content": "Hello"
        }
      ]
    }
    """

    print("Example 3: Invalid request (missing required field)")
    is_valid, result = validate_chat_request(invalid_request)
    if is_valid:
        print("✅ Valid request")
    else:
        print(f"❌ Invalid request: {result}")


if __name__ == "__main__":
    main()

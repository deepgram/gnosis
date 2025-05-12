"""
Utility for validating Chat Completion request bodies.
"""

import json
from typing import Dict, Any, Tuple, Union

from app.models.chat import ChatCompletionRequest


def validate_chat_request(
    request_json: str,
) -> Tuple[bool, Union[ChatCompletionRequest, str]]:
    """
    Validate that a JSON string can be parsed into a ChatCompletionRequest model.

    Args:
        request_json: JSON string containing a chat completion request

    Returns:
        A tuple containing:
        - bool: True if validation was successful, False otherwise
        - Union[ChatCompletionRequest, str]: Either the parsed model or an error message
    """
    try:
        # Parse JSON string to dictionary
        request_data = json.loads(request_json)

        # Try to create a ChatCompletionRequest from the parsed data
        model = ChatCompletionRequest(**request_data)

        return True, model
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON format: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def validate_chat_request_dict(
    request_data: Dict[str, Any],
) -> Tuple[bool, Union[ChatCompletionRequest, str]]:
    """
    Validate that a dictionary can be parsed into a ChatCompletionRequest model.

    Args:
        request_data: Dictionary containing a chat completion request

    Returns:
        A tuple containing:
        - bool: True if validation was successful, False otherwise
        - Union[ChatCompletionRequest, str]: Either the parsed model or an error message
    """
    try:
        # Try to create a ChatCompletionRequest from the data
        model = ChatCompletionRequest(**request_data)

        return True, model
    except Exception as e:
        return False, f"Validation error: {str(e)}"

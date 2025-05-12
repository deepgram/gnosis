from typing import Dict, List, Any, Optional
import copy
import logging
from litestar import Request
from app.services.tools.registry import (
    get_all_tool_definitions,
    get_tool_implementation,
)
from app.models.chat import (
    ChatCompletionRequest,
    Tool,
    ToolFunction,
    ToolParameters,
    ToolParameterProperty,
)


logger = logging.getLogger(__name__)


class FunctionCallingService:
    """Service for handling function calling with Deepgram and OpenAI."""

    # Prefix for internal function calls to avoid name clashes
    FUNCTION_PREFIX = "gnosis_function_"

    @staticmethod
    def get_openai_function_config() -> List[Tool]:
        """
        Get function configuration for OpenAI API.

        Returns:
            List of Tool models with prefixed names
        """
        tool_definitions = get_all_tool_definitions()

        logger.info(f"Found {len(tool_definitions)} tool definitions")

        prefixed_tools = []

        for tool_dict in tool_definitions:
            function = tool_dict.get("function", {})
            if "name" in function:
                original_name = function["name"]
                prefixed_name = FunctionCallingService.FUNCTION_PREFIX + original_name

                # Get the parameters from the function definition
                params = function.get("parameters", {})

                # Ensure the properties are properly formatted for ToolParameters
                properties_dict = {}
                if "properties" in params:
                    for prop_name, prop_details in params["properties"].items():
                        properties_dict[prop_name] = ToolParameterProperty(
                            type=prop_details.get("type", "string"),
                            description=prop_details.get("description", ""),
                            **{
                                k: v
                                for k, v in prop_details.items()
                                if k not in ["type", "description"]
                            },
                        )

                # Make sure required is a list if provided
                required_list = params.get("required", [])
                if required_list is None:
                    required_list = []

                # Create Tool model with properly structured parameters
                tool = Tool(
                    type="function",
                    function=ToolFunction(
                        name=prefixed_name,
                        description=function.get("description", ""),
                        parameters=ToolParameters(
                            type="object",
                            properties=properties_dict,
                            required=required_list,
                        ),
                    ),
                )
                prefixed_tools.append(tool)

        return prefixed_tools

    @staticmethod
    def get_deepgram_function_config() -> Dict[str, Any]:
        """
        Get function configuration for Deepgram API.

        Returns:
            Dictionary containing function definitions in Deepgram format with prefixed names
        """
        # Extract the functions from the OpenAI-formatted tool definitions
        deepgram_functions = []
        tool_definitions = get_all_tool_definitions()

        for tool in tool_definitions:
            function = tool.get("function", {})
            name = function.get("name")

            if name:
                prefixed_name = FunctionCallingService.FUNCTION_PREFIX + name
                deepgram_function = {
                    "name": prefixed_name,
                    "description": function.get("description", ""),
                    "parameters": function.get("parameters", {}),
                }
                deepgram_functions.append(deepgram_function)

        return {"functions": deepgram_functions} if deepgram_functions else {}

    @staticmethod
    async def execute_function(
        function_name: str, arguments: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Execute a registered function with the given arguments.

        Args:
            function_name: Name of the function to execute (may be prefixed)
            arguments: Arguments to pass to the function

        Returns:
            Result of the function execution or None if function not found
        """
        # Remove prefix if present
        if function_name.startswith(FunctionCallingService.FUNCTION_PREFIX):
            original_name = function_name[len(FunctionCallingService.FUNCTION_PREFIX) :]
        else:
            original_name = function_name

        function = get_tool_implementation(original_name)

        if function:
            return await function(arguments)

        return None

    @staticmethod
    def augment_openai_request(request: ChatCompletionRequest) -> ChatCompletionRequest:
        """
        Augment an OpenAI chat completion request with our function definitions.

        Args:
            request: The original OpenAI request object

        Returns:
            The augmented request with our function definitions added
        """
        # Create a deep copy to avoid modifying the original
        augmented_request = copy.deepcopy(request)

        # Get our function definitions as Tool models
        gnosis_tools = FunctionCallingService.get_openai_function_config()
        logger.info(f"Found {len(gnosis_tools)} tools")

        # If no tools are available, return the original request
        if not gnosis_tools:
            return augmented_request

        # Check if the request already has tools
        if hasattr(augmented_request, "tools") and augmented_request.tools:
            # Add our tools to the existing tools
            augmented_request.tools.extend(gnosis_tools)
        else:
            # Set our tools as the request's tools
            augmented_request.tools = gnosis_tools

        # Ensure tool_choice is properly configured if not already set
        if (
            not hasattr(augmented_request, "tool_choice")
            or augmented_request.tool_choice == "none"
        ):
            augmented_request.tool_choice = "auto"

        return augmented_request

    @staticmethod
    def augment_deepgram_agent_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Augment a Deepgram agent configuration with our function definitions.

        Args:
            config: The original Deepgram Settings object as a dictionary

        Returns:
            The augmented configuration with our function definitions added
        """
        # Create a deep copy to avoid modifying the original
        augmented_config = copy.deepcopy(config)

        # Get our function definitions for Deepgram
        gnosis_functions = FunctionCallingService.get_deepgram_function_config()

        if not gnosis_functions:
            return augmented_config

        # Make sure the agent config exists
        if "agent" not in augmented_config:
            return augmented_config

        # Make sure the think config exists
        if "think" not in augmented_config["agent"]:
            augmented_config["agent"]["think"] = {}

        # Initialize think.functions for V1 API
        if "functions" not in augmented_config["agent"]["think"]:
            augmented_config["agent"]["think"]["functions"] = {}

        # Get existing functions if any
        existing_functions = []
        if "functions" in augmented_config["agent"]["think"]:
            # Handle the functions format
            if isinstance(augmented_config["agent"]["think"]["functions"], list):
                existing_functions = augmented_config["agent"]["think"]["functions"]
            elif isinstance(augmented_config["agent"]["think"]["functions"], dict):
                # Convert dict to list format for V1 API
                try:
                    function_dict = augmented_config["agent"]["think"]["functions"]
                    existing_functions = [
                        {"name": k, **v} for k, v in function_dict.items()
                    ]
                except Exception as e:
                    existing_functions = []
            else:
                existing_functions = []

        # Merge our functions with existing ones
        if "functions" in gnosis_functions:
            gnosis_functions_array = gnosis_functions["functions"]

            # Create or update the functions field
            if not existing_functions:
                augmented_config["agent"]["think"]["functions"] = gnosis_functions_array
            else:
                # Merge with existing functions
                # For arrays, we simply append
                merged_functions = existing_functions + gnosis_functions_array
                augmented_config["agent"]["think"]["functions"] = merged_functions

        return augmented_config


function_calling = FunctionCallingService()

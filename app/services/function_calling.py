from typing import Dict, List, Any, Optional
import copy
import structlog

from app.services.tools.registry import (
    get_all_tool_definitions,
    get_tool_implementation,
)

# Get a logger for this module
log = structlog.get_logger()


class FunctionCallingService:
    """Service for handling function calling with Deepgram and OpenAI."""

    # Prefix for internal function calls to avoid name clashes
    FUNCTION_PREFIX = "gnosis_function_"

    @staticmethod
    def get_openai_function_config() -> List[Dict[str, Any]]:
        """
        Get function configuration for OpenAI API.

        Returns:
            List of function definitions in OpenAI format with prefixed names
        """
        tool_definitions = get_all_tool_definitions()
        log.debug(f"Fetched {len(tool_definitions)} tool definitions for OpenAI config")

        prefixed_tools = []

        for tool in tool_definitions:
            prefixed_tool = copy.deepcopy(tool)
            function = prefixed_tool.get("function", {})
            if "name" in function:
                original_name = function["name"]
                function["name"] = (
                    FunctionCallingService.FUNCTION_PREFIX + original_name
                )
                log.debug(f"Prefixed tool name: {original_name} -> {function['name']}")
            prefixed_tools.append(prefixed_tool)

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
        log.debug(
            f"Fetched {len(tool_definitions)} tool definitions for Deepgram config"
        )

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
                log.debug(f"Added Deepgram function: {prefixed_name}")

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
            log.debug(
                f"Removed prefix for function execution: {function_name} -> {original_name}"
            )
        else:
            original_name = function_name
            log.debug(f"No prefix found for function execution: {function_name}")

        function = get_tool_implementation(original_name)
        if function:
            log.debug(f"Executing function: {original_name}")
            result = await function(arguments)
            log.debug(f"Function execution completed: {original_name}")
            return result

        log.warning(f"Function not found for execution: {original_name}")
        return None

    @staticmethod
    def augment_openai_request(request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Augment an OpenAI chat completion request with our function definitions.

        Args:
            request: The original OpenAI request object

        Returns:
            The augmented request with our function definitions added
        """
        # Create a deep copy to avoid modifying the original
        augmented_request = copy.deepcopy(request)

        # Get our function definitions
        gnosis_tools = FunctionCallingService.get_openai_function_config()

        if not gnosis_tools:
            log.debug("No Gnosis tools available for request augmentation")
            return augmented_request

        log.debug(f"Augmenting request with {len(gnosis_tools)} Gnosis tools")

        # Check if the request already has tools
        if "tools" in augmented_request:
            existing_tools_count = len(augmented_request["tools"])
            log.debug(
                f"Request already has {existing_tools_count} tools, adding Gnosis tools"
            )
            # Add our tools to the existing tools
            augmented_request["tools"].extend(gnosis_tools)
        else:
            # Set our tools as the request's tools
            log.debug("Request has no tools, setting Gnosis tools")
            augmented_request["tools"] = gnosis_tools

        # Ensure tool_choice is properly configured if not already set
        if "tool_choice" not in augmented_request:
            augmented_request["tool_choice"] = "auto"
            log.debug("Set tool_choice to 'auto'")

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
            log.debug(
                "No Gnosis functions available for Deepgram agent configuration augmentation"
            )
            return augmented_config

        # Make sure the agent config exists
        if "agent" not in augmented_config:
            log.warning(
                "No 'agent' key found in Deepgram agent configuration, cannot augment"
            )
            return augmented_config

        # Make sure the think config exists
        if "think" not in augmented_config["agent"]:
            log.debug("No 'think' key found in agent configuration, adding one")
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
                log.debug("Converting functions dict to list format for V1 API")
                try:
                    function_dict = augmented_config["agent"]["think"]["functions"]
                    existing_functions = [
                        {"name": k, **v} for k, v in function_dict.items()
                    ]
                except Exception as e:
                    log.warning(f"Error converting functions dict: {e}")
                    existing_functions = []
            else:
                log.warning(
                    "'functions' in agent.think is not a list or dict, converting to empty list"
                )
                existing_functions = []

        log.debug(f"Found {len(existing_functions)} existing functions in agent config")

        # Merge our functions with existing ones
        if "functions" in gnosis_functions:
            gnosis_functions_array = gnosis_functions["functions"]
            log.debug(
                f"Adding {len(gnosis_functions_array)} Gnosis functions to agent configuration"
            )

            # Create or update the functions field
            if not existing_functions:
                augmented_config["agent"]["think"]["functions"] = gnosis_functions_array
            else:
                # Merge with existing functions
                # For arrays, we simply append
                merged_functions = existing_functions + gnosis_functions_array
                augmented_config["agent"]["think"]["functions"] = merged_functions
                log.debug(
                    f"Merged functions, now have {len(merged_functions)} total functions"
                )

        return augmented_config


function_calling = FunctionCallingService()

from typing import Dict, List, Any, Optional
import copy

from app.services.tools.registry import get_all_tool_definitions, tools


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
        prefixed_tools = []
        
        for tool in tool_definitions:
            prefixed_tool = copy.deepcopy(tool)
            function = prefixed_tool.get("function", {})
            if "name" in function:
                function["name"] = FunctionCallingService.FUNCTION_PREFIX + function["name"]
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
        deepgram_functions = {}
        
        for tool in get_all_tool_definitions():
            function = tool.get("function", {})
            name = function.get("name")
            
            if name:
                prefixed_name = FunctionCallingService.FUNCTION_PREFIX + name
                deepgram_functions[prefixed_name] = {
                    "description": function.get("description", ""),
                    "parameters": function.get("parameters", {})
                }
        
        return {"functions": deepgram_functions} if deepgram_functions else {}
    
    @staticmethod
    async def execute_function(function_name: str, arguments: Dict[str, Any]) -> Optional[Any]:
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
            original_name = function_name[len(FunctionCallingService.FUNCTION_PREFIX):]
        else:
            original_name = function_name
            
        function = tools.get(original_name)
        if function:
            return await function(arguments)
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
            return augmented_request
            
        # Check if the request already has tools
        if "tools" in augmented_request:
            # Add our tools to the existing tools
            augmented_request["tools"].extend(gnosis_tools)
        else:
            # Set our tools as the request's tools
            augmented_request["tools"] = gnosis_tools
            
        # Ensure tool_choice is properly configured if not already set
        if "tool_choice" not in augmented_request:
            augmented_request["tool_choice"] = "auto"
            
        return augmented_request


function_calling = FunctionCallingService() 
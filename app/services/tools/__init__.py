from app.services.tools import registry
from app.services.tools import vector_search

# Register tool definitions using the descriptions from vector_search module
for tool_name, tool_info in vector_search.TOOL_DESCRIPTIONS.items():
    registry.register_tool_definition(
        name=tool_info["name"],
        description=tool_info["description"],
        parameters=tool_info["parameters"]
    ) 
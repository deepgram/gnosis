"""
Pydantic models for tool definitions and tool responses.
"""

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

from app.models.chat import (
    ToolCall,
)


class RegistryItem(BaseModel):
    """Registry item."""

    implementation: Optional[Any] = None
    definition: Optional[ToolCall] = None
    scope: str = "public"


class ToolRegistry(BaseModel):
    """
    Registry for tools and their definitions.

    The registry is now a unified structure where each tool has both
    an implementation and a definition, allowing for simpler registration
    and access.
    """

    registry: Dict[str, RegistryItem] = Field(default_factory=dict)

    def get_implementation(self, name: str) -> Optional[Any]:
        """Get a tool implementation by name."""
        registry_item = self.registry.get(name)
        return registry_item.implementation if registry_item else None

    def get_definition(self, name: str) -> Optional[ToolCall]:
        """Get a tool definition by name."""
        registry_item = self.registry.get(name)
        return registry_item.definition if registry_item else None

    def get_all_definitions(self) -> List[ToolCall]:
        """Get all tool definitions."""
        return [
            item.definition
            for item in self.registry.values()
            if item.definition is not None
        ]

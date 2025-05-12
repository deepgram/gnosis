"""
RAG (Retrieval Augmented Generation) service.

This service handles vector search and context augmentation for LLM responses.
"""

import structlog
from typing import List

from app.models.chat import ChatMessage

# Get a logger for this module
log = structlog.get_logger()


class RequestAugmentedGenerationService:
    """Service for handling Retrieval Augmented Generation operations."""

    @staticmethod
    def is_conversation_continuation(
        messages: List[ChatMessage],
    ) -> bool:
        """
        Check if the conversation is a continuation of a previous thread by looking for
        assistant or tool responses in the messages.

        Args:
            messages: List of chat messages

        Returns:
            True if this is a continuation, False if it's a new conversation
        """
        if not messages:
            return False

        # Count user and non-user messages
        user_messages = 0
        non_user_messages = 0

        for message in messages:
            role = message.role

            if role == "user":
                user_messages += 1
            elif role in ["assistant", "tool"]:
                non_user_messages += 1

        # A conversation is a continuation if it has non-user messages
        # AND more than one user message
        return non_user_messages > 0 or user_messages > 1

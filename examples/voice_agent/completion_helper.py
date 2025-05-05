#!/usr/bin/env python3
# completion_helper.py
# Helper module for generating conversation continuations using OpenAI

import os
import requests
import json
import time
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv


class OpenAICompletionHelper:
    """Helper class for generating conversational continuations using OpenAI"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        dry_run: bool = False,
    ):
        """
        Initialize the completion helper

        Args:
            api_key: OpenAI API key (will use OPENAI_API_KEY from env vars if not provided)
            model: OpenAI model to use (default: gpt-4o-mini)
            dry_run: If True, skip actual API calls and use dummy data (for testing)
        """
        # Load environment variables from .env files
        self._load_env_files()

        # Get API key from args, env var, or raise error
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key and not dry_run:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass it to the constructor."
            )

        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
            "Content-Type": "application/json",
        }
        self.model = model
        self.dry_run = dry_run

        # Initialize conversation history
        self.conversation_history = []

    def _load_env_files(self):
        """Load environment variables from multiple possible .env file locations"""
        # Try to load from project root .env file (2 directories up from this file)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))

        # List of potential env file locations in order of precedence
        env_paths = [
            os.path.join(os.getcwd(), ".env"),  # Current working directory
            os.path.join(script_dir, ".env"),  # Script directory
            os.path.join(root_dir, ".env"),  # Project root
            os.path.expanduser("~/.env"),  # User's home directory
        ]

        print(f"Loading environment variables from: {env_paths}")

        # Try loading from each location
        for env_path in env_paths:
            if os.path.exists(env_path):
                print(f"Loading environment from: {env_path}")
                load_dotenv(env_path)
                break

    def add_message(self, role: str, content: str):
        """
        Add a message to the conversation history

        Args:
            role: The role of the message sender ('user' or 'assistant')
            content: The message content
        """
        self.conversation_history.append({"role": role, "content": content})

    def generate_response(self, system_prompt: Optional[str] = None) -> str:
        """
        Generate a response based on the conversation history

        Args:
            system_prompt: Optional system prompt to guide the conversation

        Returns:
            Generated response text
        """
        if self.dry_run:
            print("[DRY RUN] Simulating OpenAI API call")
            return "This is a test response. I would continue the conversation here."

        # Create messages array with optional system prompt
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add conversation history
        messages.extend(self.conversation_history)

        # Make the API request
        start_time = time.time()
        print(f"Generating response using {self.model}...")

        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={"model": self.model, "messages": messages, "temperature": 0.7},
            )

            # Check for errors
            if response.status_code != 200:
                error_msg = f"OpenAI API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data.get('error', {}).get('message', '')}"
                except:
                    pass
                raise Exception(error_msg)

            # Extract response text
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"]

            # Add assistant response to history
            self.add_message("assistant", content)

            duration = time.time() - start_time
            print(f"Response generated in {duration:.2f}s")

            return content

        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return "I'm sorry, there was an error generating a response."

    def continue_conversation(
        self,
        agent_response: str,
        system_prompt: str = "You are a helpful assistant continuing a conversation based on previous responses. Generate a natural, brief follow-up response or question to the last message.",
    ) -> str:
        """
        Continue the conversation based on an agent's response

        Args:
            agent_response: The last response from the agent
            system_prompt: System prompt to guide the continuation

        Returns:
            Generated message to continue the conversation
        """
        # Add agent's response to history
        self.add_message("assistant", agent_response)

        # Generate our next message
        print(
            f"Generating continuation based on agent response: '{agent_response[:50]}{'...' if len(agent_response) > 50 else ''}'"
        )

        # Create a complete messages array with system prompt
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.conversation_history)

        # Add a final prompt asking for the next message
        messages.append(
            {
                "role": "user",
                "content": "Based on this conversation, please generate a natural follow-up message or question that I should say next to continue the conversation. Keep it brief and conversational.",
            }
        )

        # Make the API request
        if self.dry_run:
            continuation = "Tell me more about that. I'm really interested."
        else:
            try:
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.7,
                    },
                )

                # Check for errors
                if response.status_code != 200:
                    error_msg = f"OpenAI API error: {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg = f"{error_msg} - {error_data.get('error', {}).get('message', '')}"
                    except:
                        pass
                    raise Exception(error_msg)

                # Extract response text
                response_data = response.json()
                continuation = response_data["choices"][0]["message"]["content"]

            except Exception as e:
                print(f"Error generating continuation: {str(e)}")
                continuation = "That's interesting. Can you tell me more?"

        # Add our response to the conversation history
        self.add_message("user", continuation)

        print(f"Generated continuation: '{continuation}'")
        return continuation


# Command-line interface for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate conversational responses using OpenAI"
    )
    parser.add_argument("--message", required=True, help="Message to respond to")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model to use")
    parser.add_argument("--api-key", help="OpenAI API key (overrides env vars)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Skip actual API calls (for testing)"
    )

    args = parser.parse_args()

    # Create helper and generate response
    helper = OpenAICompletionHelper(
        api_key=args.api_key, model=args.model, dry_run=args.dry_run
    )

    # Add user message
    helper.add_message("user", args.message)

    # Generate response
    response = helper.generate_response()

    print(f"\nUser: {args.message}")
    print(f"Assistant: {response}")

    # Generate continuation example
    print("\nDemo conversation continuation:")
    continuation = helper.continue_conversation(response)
    print(f"Next user message: {continuation}")


# Quick example function for direct use
def quick_completion(message, api_key=None):
    """
    Simple function to generate a response to a message

    Args:
        message: Message to respond to
        api_key: Optional OpenAI API key (uses env var if not provided)

    Returns:
        Generated response text
    """
    helper = OpenAICompletionHelper(api_key=api_key)
    helper.add_message("user", message)
    return helper.generate_response()

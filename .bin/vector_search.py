#!/usr/bin/env python3
# vector_search.py
# Simple standalone vector search tool

import sys
import os
import requests
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv


def load_env_files():
    """Load environment variables from multiple possible .env file locations"""
    # Try different possible locations for .env file
    env_paths = [
        os.path.join(os.getcwd(), ".env"),  # Current working directory
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)), ".env"
        ),  # Script directory
        os.path.expanduser("~/.env"),  # User's home directory
    ]

    # Try loading from each location
    for env_path in env_paths:
        if os.path.exists(env_path):
            print(f"Loading environment from: {env_path}")
            load_dotenv(env_path)
            return


def search_vector_store(
    query: str, limit: int = 5, score_threshold: float = 0.9
) -> Dict[str, Any]:
    """
    Search the OpenAI vector store and return raw results

    Args:
        query: The search query
        limit: Maximum number of results to return
        score_threshold: Minimum similarity score threshold (0-1)

    Returns:
        Raw API response as a dictionary
    """
    # Load API key from environment
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # Get vector store ID from environment or use default
    vector_store_id = os.environ.get(
        "OPENAI_VECTOR_STORE_ID", "vs_67ff646e0558819189933696b5b165b1"
    )

    # Construct the URL
    target_url = f"https://api.openai.com/v1/vector_stores/{vector_store_id}/search"

    # Prepare headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Prepare the request payload
    payload = {
        "query": query,
        "max_num_results": limit,
        "ranking_options": {
            "score_threshold": score_threshold,
        },
    }

    # Make the request
    print(f"Searching for: '{query}'")
    response = requests.post(target_url, headers=headers, json=payload)

    # Check for errors
    if response.status_code != 200:
        error_msg = f"Vector search error: {response.status_code}"
        try:
            error_data = response.json()
            error_msg = (
                f"{error_msg} - {error_data.get('error', {}).get('message', '')}"
            )
        except:
            pass
        raise Exception(error_msg)

    # Return the raw response
    return response.json()


def main():
    """Main entry point for the script"""
    # Load environment variables
    load_env_files()

    # Check for query argument
    if len(sys.argv) < 2:
        print("Usage: python vector_search.py 'your search query'")
        sys.exit(1)

    # Extract query from command line arguments
    query = " ".join(sys.argv[1:])

    try:
        # Perform the search
        results = search_vector_store(query)

        # Print the raw JSON result
        print(json.dumps(results, indent=2))

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import json
import requests
import argparse
import colorama
from colorama import Fore, Style

# Initialize colorama for cross-platform color support
colorama.init()


def main():
    parser = argparse.ArgumentParser(description="Tool Calling Test for Gnosis")
    parser.add_argument(
        "--host", default="http://localhost:8080", help="Base URL of the Gnosis API"
    )
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use")
    parser.add_argument(
        "--system",
        default="""
You are a helpful assistant responsible for searching and retrieving information.
When asked about technical documentation, ALWAYS use the search_documentation tool.
                       """,
        help="System message",
    )
    parser.add_argument(
        "--user",
        default="Find information about Deepgram's Nova-2 model and its features",
        help="User message",
    )
    parser.add_argument("--stream", action="store_true", help="Enable streaming mode")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    endpoint = f"{args.host}/v1/chat/completions"

    # Print header
    print(f"{Style.BRIGHT}{Fore.CYAN}Tool Calling Test Example{Style.RESET_ALL}")
    print("═════════════════════════════════════════")
    print(f"{Style.BRIGHT}Model:{Style.RESET_ALL} {args.model}")
    print(f"{Style.BRIGHT}Host:{Style.RESET_ALL} {args.host}")
    print(
        f"{Style.BRIGHT}Streaming:{Style.RESET_ALL} {'Enabled' if args.stream else 'Disabled'}"
    )
    print("═════════════════════════════════════════")

    # Prepare the request
    request_data = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": args.system},
            {"role": "user", "content": args.user},
        ],
        "stream": args.stream,
        "temperature": 0.7,
        "max_tokens": 2048,
        "tool_choice": "auto",  # Enable automatic tool calling
    }

    if args.verbose:
        print(f"{Fore.CYAN}[VERBOSE]{Style.RESET_ALL} Request data:")
        print(json.dumps(request_data, indent=2))

    log("Sending chat completion request...", "important", args.verbose)
    print(f"\n{Style.BRIGHT}User:{Style.RESET_ALL} {args.user}\n")
    print(f"{Style.BRIGHT}{Fore.GREEN}Assistant:{Style.RESET_ALL} ", end="", flush=True)

    if args.stream:
        # Handle streaming response
        response = requests.post(
            endpoint,
            json=request_data,
            headers={"Content-Type": "application/json"},
            stream=True,
        )

        # Process the streaming response
        for line in response.iter_lines():
            if not line:
                continue

            line = line.decode("utf-8")
            if not line.startswith("data: "):
                continue

            data = line[6:]  # Remove 'data: ' prefix

            if data == "[DONE]":
                break

            try:
                json_data = json.loads(data)

                if args.verbose:
                    log(f"Received chunk: {data}", "debug", args.verbose)

                # Extract content from the delta
                if "choices" in json_data and len(json_data["choices"]) > 0:
                    delta = json_data["choices"][0].get("delta", {})

                    if "content" in delta and delta["content"]:
                        # Print content immediately as it arrives
                        print(delta["content"], end="", flush=True)
            except json.JSONDecodeError:
                if args.verbose:
                    log(f"Error parsing JSON: {data}", "error", args.verbose)
    else:
        # Handle non-streaming response
        response = requests.post(
            endpoint, json=request_data, headers={"Content-Type": "application/json"}
        )

        if args.verbose:
            log(f"Response status: {response.status_code}", "info", args.verbose)

        try:
            response_data = response.json()

            if args.verbose:
                log("Full response:", "debug", args.verbose)
                print(json.dumps(response_data, indent=2))

            # Extract and print the content
            if "choices" in response_data and len(response_data["choices"]) > 0:
                content = response_data["choices"][0]["message"].get("content", "")
                print(content)

                # Check for tool calls
                if "tool_calls" in response_data["choices"][0]["message"]:
                    tool_calls = response_data["choices"][0]["message"]["tool_calls"]
                    log(
                        f"Found {len(tool_calls)} tool calls in response",
                        "important",
                        True,
                    )

                    for i, tool_call in enumerate(tool_calls):
                        log(f"Tool call #{i+1}:", "important", True)
                        print(json.dumps(tool_call, indent=2))
            else:
                log("Unexpected response format", "error", args.verbose)
                print(json.dumps(response_data, indent=2))
        except json.JSONDecodeError:
            log(f"Error parsing response: {response.text}", "error", args.verbose)
            print(response.text)

    print("\n")
    log("Request completed.", "important", args.verbose)


def log(message, level="info", verbose=False):
    """Log a message with appropriate formatting if verbose mode is enabled."""
    if not verbose and level != "important":
        return

    prefix = ""
    if level == "info":
        prefix = f"{Fore.CYAN}[INFO]{Style.RESET_ALL}"
    elif level == "important":
        prefix = f"{Fore.YELLOW}[IMPORTANT]{Style.RESET_ALL}"
    elif level == "error":
        prefix = f"{Fore.RED}[ERROR]{Style.RESET_ALL}"
    elif level == "debug":
        prefix = f"{Fore.MAGENTA}[DEBUG]{Style.RESET_ALL}"

    print(f"{prefix} {message}")


if __name__ == "__main__":
    main()

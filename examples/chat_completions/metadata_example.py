#!/usr/bin/env python3
import json
import requests
import argparse
import colorama
from typing import Dict, Any
from colorama import Fore, Style
from datetime import datetime

# Initialize colorama for cross-platform color support
colorama.init()


def main():
    parser = argparse.ArgumentParser(description="Metadata Example for Gnosis")
    parser.add_argument(
        "--host", default="http://localhost:8080", help="Base URL of the Gnosis API"
    )
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model to use")
    parser.add_argument(
        "--system",
        default="""
You are a helpful assistant responsible for answering questions.

Prioritize extremely small example code followed by a link to the correct documentation.

Unless they ask for a specific code language, use a cURL example.
                       """,
        help="System message",
    )
    parser.add_argument(
        "--user",
        default="Search for documentation about Deepgram transcription API",
        help="User message",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Enable streaming mode (note: metadata not available in streaming mode)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    endpoint = f"{args.host}/v1/chat/completions"

    # Print header
    print(f"{Style.BRIGHT}{Fore.CYAN}Gnosis Metadata Example{Style.RESET_ALL}")
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
        "response_format": {"type": "text"},
        "temperature": 1,
        "max_completion_tokens": 2048,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0,
    }

    if args.verbose:
        print(f"{Fore.CYAN}[VERBOSE]{Style.RESET_ALL} Request data:")
        print(json.dumps(request_data, indent=2))

    log("Sending chat completion request...", "important", args.verbose)
    start_time = datetime.now()
    print(f"\n{Style.BRIGHT}User:{Style.RESET_ALL} {args.user}\n")

    if args.stream:
        print(
            f"{Fore.YELLOW}[WARNING] Metadata is not available in streaming mode{Style.RESET_ALL}"
        )
        print(
            f"{Style.BRIGHT}{Fore.GREEN}Assistant:{Style.RESET_ALL} ",
            end="",
            flush=True,
        )

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

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() * 1000  # in milliseconds

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
                print(
                    f"{Style.BRIGHT}{Fore.GREEN}Assistant:{Style.RESET_ALL} {content}"
                )

                # Check for metadata
                print_metadata_report(response_data, duration)

            else:
                log("Unexpected response format", "error", args.verbose)
                print(json.dumps(response_data, indent=2))
        except json.JSONDecodeError:
            log(f"Error parsing response: {response.text}", "error", args.verbose)
            print(response.text)

    print("\n")
    log("Request completed.", "important", args.verbose)


def print_metadata_report(
    response_data: Dict[str, Any], total_request_duration: float
) -> None:
    """Print a detailed report of metadata and token usage."""
    print("\n" + "═" * 60)
    print(f"{Style.BRIGHT}{Fore.CYAN}GNOSIS METADATA REPORT{Style.RESET_ALL}")
    print("═" * 60)

    # Check if metadata exists
    if "gnosis_metadata" not in response_data:
        print(f"{Fore.RED}No Gnosis metadata available in response{Style.RESET_ALL}")
        return

    metadata = response_data["gnosis_metadata"]

    # 1. Summary Section
    print(f"\n{Style.BRIGHT}Summary:{Style.RESET_ALL}")
    print(f"  • {metadata.get('summary', 'No summary available')}")
    print(f"  • Total latency: {metadata.get('total_latency_ms', 'N/A'):.2f}ms")
    if "usage" in response_data:
        usage = response_data["usage"]
        print(
            f"  • API Token Usage: {usage.get('prompt_tokens', 0)} prompt + "
            f"{usage.get('completion_tokens', 0)} completion = "
            f"{usage.get('total_tokens', 0)} total tokens"
        )

    # 2. Operations Breakdown
    operations = metadata.get("operations", [])
    if operations:
        print(f"\n{Style.BRIGHT}Operations:{Style.RESET_ALL}")

        # Group operations by type
        op_by_type = {}
        for op in operations:
            op_type = op.get("operation_type", "unknown")
            if op_type not in op_by_type:
                op_by_type[op_type] = []
            op_by_type[op_type].append(op)

        # Print each operation type
        for op_type, ops in op_by_type.items():
            print(
                f"\n  {Style.BRIGHT}{op_type.upper()} OPERATIONS ({len(ops)}){Style.RESET_ALL}"
            )

            for i, op in enumerate(ops, 1):
                name = op.get("name", "unnamed")
                latency = op.get("latency_ms", "N/A")
                tokens = op.get("tokens", "N/A")

                print(f"  {i}. {Fore.YELLOW}{name}{Style.RESET_ALL}")
                print(
                    f"     • Latency: {latency if latency == 'N/A' else f'{latency:.2f}ms'}"
                )
                print(f"     • Tokens: {tokens}")

                # Print operation details if available
                details = op.get("details", {})
                if details:
                    if "query" in details:
                        print(f"     • Query: \"{details['query']}\"")
                    if "result_count" in details:
                        print(f"     • Results: {details['result_count']}")
                    if "tool_call_id" in details:
                        print(f"     • Tool Call ID: {details['tool_call_id']}")
                    if "is_internal" in details:
                        print(f"     • Internal: {details['is_internal']}")
                    if "arguments" in details and details["arguments"] != "{}":
                        print(f"     • Arguments: {details['arguments']}")
                    if "result_type" in details:
                        print(f"     • Result type: {details['result_type']}")
                    if "error" in details:
                        print(
                            f"     • {Fore.RED}Error: {details['error']}{Style.RESET_ALL}"
                        )

    # 3. Performance Metrics
    print(f"\n{Style.BRIGHT}Performance Metrics:{Style.RESET_ALL}")
    print(f"  • Client-measured total duration: {total_request_duration:.2f}ms")
    if "total_latency_ms" in metadata:
        server_latency = metadata["total_latency_ms"]
        print(f"  • Server-measured latency: {server_latency:.2f}ms")
        print(f"  • Network overhead: {total_request_duration - server_latency:.2f}ms")
    print("═" * 60)


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

#!/usr/bin/env python3
import json
import requests
import argparse
import sys
import colorama
from colorama import Fore, Style

# Initialize colorama for cross-platform color support
colorama.init()

# Custom JSON encoder to handle non-serializable objects
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        # Convert non-serializable objects to strings
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)

def main():
    parser = argparse.ArgumentParser(description="Deepgram RAG Example using Gnosis")
    parser.add_argument("--host", default="http://localhost:8080", help="Base URL of the Gnosis API")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use")
    parser.add_argument("--question", 
                      default="What is Deepgram and what features does it offer?",
                      help="Question about Deepgram")
    parser.add_argument("--stream", action="store_true", help="Enable streaming mode")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()
    
    endpoint = f"{args.host}/v1/chat/completions"
    
    # Print header
    print(f"{Style.BRIGHT}{Fore.CYAN}Deepgram RAG Example{Style.RESET_ALL}")
    print("═════════════════════════════════════════")
    print(f"{Style.BRIGHT}Model:{Style.RESET_ALL} {args.model}")
    print(f"{Style.BRIGHT}Question:{Style.RESET_ALL} {args.question}")
    print("═════════════════════════════════════════")
    
    # System message to indicate we want Deepgram information
    system_message = "You are a helpful assistant with knowledge about Deepgram. Answer questions about Deepgram accurately and concisely."
    
    # Prepare the request
    request_data = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": args.question}
        ],
        "temperature": 0.7,
        "stream": args.stream
    }
    
    if args.verbose:
        print(f"{Fore.CYAN}[VERBOSE]{Style.RESET_ALL} Request data:")
        print(json.dumps(request_data, indent=2))
    
    log("Sending chat completion request about Deepgram...", "important", args.verbose)
    print(f"\n{Style.BRIGHT}User:{Style.RESET_ALL} {args.question}\n")
    print(f"{Style.BRIGHT}{Fore.GREEN}Assistant:{Style.RESET_ALL} ", end="", flush=True)
    
    if args.stream:
        # Handle streaming response
        response = requests.post(
            endpoint,
            json=request_data,
            headers={"Content-Type": "application/json"},
            stream=True
        )
        
        # Check if the response status is not 200
        if response.status_code != 200:
            print(f"\n{Fore.RED}Error: Received status code {response.status_code}{Style.RESET_ALL}")
            try:
                # Try to safely print the error response
                try:
                    error_data = response.json()
                    print(f"Error details: {json.dumps(error_data, indent=2, cls=CustomEncoder)}")
                except (json.JSONDecodeError, TypeError):
                    print(f"Error response: {response.text}")
            except Exception as e:
                print(f"Error processing response: {str(e)}")
            sys.exit(1)
        
        # Process the streaming response
        for line in response.iter_lines():
            if not line:
                continue
                
            line = line.decode('utf-8')
            if not line.startswith('data: '):
                continue
                
            data = line[6:]  # Remove 'data: ' prefix
            
            if data == "[DONE]":
                break
                
            try:
                json_data = json.loads(data)
                
                # Extract content from the delta
                if 'choices' in json_data and len(json_data['choices']) > 0:
                    delta = json_data['choices'][0].get('delta', {})
                    
                    if 'content' in delta and delta['content']:
                        # Print content immediately as it arrives
                        print(delta['content'], end='', flush=True)
            except json.JSONDecodeError:
                if args.verbose:
                    log(f"Error parsing JSON: {data}", "error", args.verbose)
    else:
        # Handle non-streaming response
        response = requests.post(
            endpoint,
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        if args.verbose:
            log(f"Response status: {response.status_code}", "info", args.verbose)
        
        # Check if the response status is not 200
        if response.status_code != 200:
            print(f"\n{Fore.RED}Error: Received status code {response.status_code}{Style.RESET_ALL}")
            try:
                # Try to safely print the error response
                try:
                    error_data = response.json()
                    print(f"Error details: {json.dumps(error_data, indent=2, cls=CustomEncoder)}")
                except (json.JSONDecodeError, TypeError):
                    print(f"Error response: {response.text}")
            except Exception as e:
                print(f"Error processing response: {str(e)}")
            sys.exit(1)
        
        try:
            response_data = response.json()
            
            if args.verbose:
                log("Full response:", "debug", args.verbose)
                # Use the custom encoder for printing
                print(json.dumps(response_data, indent=2, cls=CustomEncoder))
            
            # Extract and print the content
            if 'choices' in response_data and len(response_data['choices']) > 0:
                content = response_data['choices'][0]['message'].get('content', '')
                print(content)
            else:
                log("Unexpected response format", "error", args.verbose)
                # Use the custom encoder for printing
                print(json.dumps(response_data, indent=2, cls=CustomEncoder))
                sys.exit(1)  # Exit with error if the response format is unexpected
        except json.JSONDecodeError:
            log(f"Error parsing response: {response.text}", "error", args.verbose)
            print(response.text)
            sys.exit(1)  # Exit with error if we can't parse the response
        except TypeError as e:
            # Handle case where response contains non-serializable objects
            log(f"Error serializing response: {str(e)}", "error", True)
            print(f"Response contains non-serializable objects: {str(e)}")
            # Try to extract just the content using a safer approach
            try:
                if 'choices' in response_data and len(response_data['choices']) > 0:
                    content = response_data['choices'][0]['message'].get('content', '')
                    if content:
                        print(content)
                    else:
                        print("No readable content found in response.")
                else:
                    print(f"Response structure: {str(response_data)[:500]}...")
            except Exception:
                print("Unable to extract content from response.")
            sys.exit(1)
    
    print("\n")
    log("Request completed.", "important", args.verbose)
    sys.exit(0)  # Exit with success if everything went well

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
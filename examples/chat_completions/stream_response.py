#!/usr/bin/env python3
import json
import requests
import argparse
import sys
import colorama
from colorama import Fore, Style

# Initialize colorama for cross-platform color support
colorama.init()

def main():
    parser = argparse.ArgumentParser(description="Streaming chat completion example")
    parser.add_argument("--host", default="http://localhost:8080", help="Base URL of the Gnosis API")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use")
    parser.add_argument("--question", 
                       default="Explain the concept of quantum computing and how it differs from classical computing. Include the principles of superposition and entanglement, and discuss potential future applications.",
                       help="Question to ask")
    parser.add_argument("--system-message", 
                       default="You are a helpful, detailed assistant who provides comprehensive explanations.",
                       help="System message to use")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()
    
    endpoint = f"{args.host}/v1/chat/completions"
    
    # Print header
    print(f"{Style.BRIGHT}{Fore.CYAN}Streamed Chat Completion Example{Style.RESET_ALL}")
    print("═════════════════════════════════════════")
    print(f"{Style.BRIGHT}Model:{Style.RESET_ALL} {args.model}")
    print(f"{Style.BRIGHT}Question:{Style.RESET_ALL} {args.question}")
    print("═════════════════════════════════════════")
    
    # Prepare the request
    request_data = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": args.system_message},
            {"role": "user", "content": args.question}
        ],
        "temperature": 0.7,
        "max_tokens": 800,
        "stream": True
    }
    
    if args.debug:
        print(f"{Fore.MAGENTA}[DEBUG]{Style.RESET_ALL} Request: {json.dumps(request_data, indent=2)}")
    
    print(f"{Style.BRIGHT}Sending request to {endpoint}...{Style.RESET_ALL}")
    print(f"\n{Style.BRIGHT}{Fore.GREEN}Assistant:{Style.RESET_ALL} ", end="", flush=True)
    
    # Send the request and process the streaming response
    response = requests.post(
        endpoint,
        json=request_data,
        headers={"Content-Type": "application/json"},
        stream=True
    )
    
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
            if args.debug:
                print(f"\n{Fore.MAGENTA}[DEBUG]{Style.RESET_ALL} Raw chunk: {data}", file=sys.stderr)
                
            json_data = json.loads(data)
            
            # Extract content from the delta
            if 'choices' in json_data and len(json_data['choices']) > 0:
                delta = json_data['choices'][0].get('delta', {})
                
                if 'content' in delta and delta['content']:
                    # Print content immediately as it arrives
                    print(delta['content'], end='', flush=True)
        except json.JSONDecodeError:
            if args.debug:
                print(f"\n{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to parse JSON: {data}", file=sys.stderr)
    
    print("\n\n" + f"{Style.BRIGHT}{Fore.CYAN}Stream completed.{Style.RESET_ALL}")

if __name__ == "__main__":
    main() 
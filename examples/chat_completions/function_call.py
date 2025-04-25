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
    parser = argparse.ArgumentParser(description="Function calling example with OpenAI API through Gnosis")
    parser.add_argument("--host", default="http://localhost:8080", help="Base URL of the Gnosis API")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use")
    parser.add_argument("--stream", action="store_true", help="Enable streaming mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()
    
    endpoint = f"{args.host}/v1/chat/completions"
    
    # Define our function schema
    functions = [{
        "type": "function",
        "function": {
            "name": "add_numbers",
            "description": "Add two numbers together",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "The first number"},
                    "b": {"type": "number", "description": "The second number"}
                },
                "required": ["a", "b"]
            }
        }
    }]
    
    # Print header
    print(f"{Style.BRIGHT}{Fore.CYAN}OpenAI Function Calling Example{Style.RESET_ALL}")
    print("═════════════════════════════════════════")
    print(f"{Style.BRIGHT}Model:{Style.RESET_ALL} {args.model}")
    print(f"{Style.BRIGHT}Function:{Style.RESET_ALL} add_numbers (adds two numbers together)")
    print("═════════════════════════════════════════")
    
    # Starting conversation
    print(f"{Style.BRIGHT}Starting conversation...{Style.RESET_ALL}\n")
    print(f"{Style.BRIGHT}User:{Style.RESET_ALL} Can you please add 12345 and 67890 for me?\n")
    
    # Initial request
    initial_request = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant who can add numbers. When asked to add numbers, use the add_numbers function."},
            {"role": "user", "content": "Can you please add 12345 and 67890 for me?"}
        ],
        "tools": functions,
        "temperature": 0.7,
        "stream": args.stream
    }
    
    log("Sending initial request...", "important", args)
    print(f"{Style.BRIGHT}{Fore.GREEN}Assistant:{Style.RESET_ALL} ", end="", flush=True)
    
    if args.stream:
        # Streaming approach
        response = requests.post(
            endpoint, 
            json=initial_request,
            headers={"Content-Type": "application/json"},
            stream=True
        )
        
        function_name = None
        function_args = None
        tool_call_id = None
        
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
                
                if args.debug:
                    log(f"Debug data: {json.dumps(json_data)}", "debug", args)
                
                # Extract content or tool calls
                if 'choices' in json_data and len(json_data['choices']) > 0:
                    delta = json_data['choices'][0].get('delta', {})
                    
                    # Check for tool calls in this chunk
                    if 'tool_calls' in delta:
                        tool_call = delta['tool_calls'][0]
                        
                        # Collect tool call ID
                        if 'id' in tool_call:
                            tool_call_id = tool_call['id']
                            
                        # Collect function name
                        if 'function' in tool_call:
                            if 'name' in tool_call['function']:
                                function_name = tool_call['function']['name']
                                
                            # Accumulate function arguments
                            if 'arguments' in tool_call['function']:
                                args_chunk = tool_call['function']['arguments']
                                if function_args is None:
                                    function_args = args_chunk
                                else:
                                    function_args += args_chunk
                    
                    # Print any content
                    if 'content' in delta and delta['content']:
                        print(delta['content'], end='', flush=True)
            except json.JSONDecodeError:
                log(f"Error parsing JSON: {data}", "error", args)
    else:
        # Non-streaming approach
        log("Using non-streaming mode", "info", args)
        response = requests.post(endpoint, json=initial_request)
        
        try:
            response_data = response.json()
            
            if args.debug:
                log(f"Debug response: {json.dumps(response_data, indent=2)}", "debug", args)
            
            if 'choices' in response_data and len(response_data['choices']) > 0:
                message = response_data['choices'][0]['message']
                
                # Check for content
                if message.get('content'):
                    print(message['content'])
                
                # Check for tool calls
                if 'tool_calls' in message and message['tool_calls']:
                    tool_call = message['tool_calls'][0]
                    function_name = tool_call['function']['name']
                    function_args = tool_call['function']['arguments']
                    tool_call_id = tool_call['id']
            else:
                log("Unexpected response format - no choices found", "error", args)
                if args.debug:
                    print(json.dumps(response_data, indent=2))
                return
        except json.JSONDecodeError:
            log(f"Error parsing response as JSON: {response.text}", "error", args)
            return
        except Exception as e:
            log(f"Error processing response: {str(e)}", "error", args)
            return
    
    # Handle function call if detected
    if function_name and function_args:
        # Parse function arguments
        try:
            # Handle string or dict arguments
            if isinstance(function_args, str):
                arguments = json.loads(function_args)
            else:
                arguments = function_args
                
            log(f"Function call detected: {function_name}", "important", args)
            
            # Execute the function
            if function_name == "add_numbers":
                a = arguments.get("a")
                b = arguments.get("b")
                
                if a is None or b is None:
                    log("Missing required parameters a or b", "error", args)
                    return
                
                result = a + b
                function_result = {"result": result}
                
                print(f"\n{Style.BRIGHT}{Fore.BLUE}Function Called:{Style.RESET_ALL} {function_name}")
                print(f"{Style.BRIGHT}Arguments:{Style.RESET_ALL} {json.dumps(arguments)}")
                print(f"{Style.BRIGHT}Result:{Style.RESET_ALL} {json.dumps(function_result)}\n")
                
                # Send result back to the model
                print(f"{Style.BRIGHT}Sending function result back to AI...{Style.RESET_ALL}\n")
                
                # Prepare follow-up request
                follow_up_request = {
                    "model": args.model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant who can add numbers."},
                        {"role": "user", "content": "Can you please add 12345 and 67890 for me?"},
                        {
                            "role": "assistant", 
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": tool_call_id,
                                    "type": "function",
                                    "function": {
                                        "name": function_name,
                                        "arguments": json.dumps(arguments)
                                    }
                                }
                            ]
                        },
                        {
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": json.dumps(function_result)
                        }
                    ],
                    "tools": functions,
                    "temperature": 0.7,
                    "stream": args.stream
                }
                
                if args.debug:
                    log(f"Follow-up request: {json.dumps(follow_up_request, indent=2)}", "debug", args)
                
                # Get final response from AI
                print(f"{Style.BRIGHT}{Fore.GREEN}Assistant:{Style.RESET_ALL} ", end="", flush=True)
                
                if args.stream:
                    # Handle streaming response
                    response = requests.post(
                        endpoint,
                        json=follow_up_request,
                        headers={"Content-Type": "application/json"},
                        stream=True
                    )
                    
                    for line in response.iter_lines():
                        if not line:
                            continue
                            
                        line = line.decode('utf-8')
                        if not line.startswith('data: '):
                            continue
                            
                        data = line[6:]
                        
                        if data == "[DONE]":
                            break
                            
                        try:
                            json_data = json.loads(data)
                            
                            if 'choices' in json_data and len(json_data['choices']) > 0:
                                delta = json_data['choices'][0].get('delta', {})
                                
                                if 'content' in delta and delta['content']:
                                    print(delta['content'], end='', flush=True)
                        except json.JSONDecodeError:
                            log(f"Error parsing JSON: {data}", "error", args)
                else:
                    # Handle non-streaming response
                    response = requests.post(endpoint, json=follow_up_request)
                    
                    try:
                        response_data = response.json()
                        
                        if args.debug:
                            log(f"Final response: {json.dumps(response_data, indent=2)}", "debug", args)
                        
                        if 'choices' in response_data and len(response_data['choices']) > 0:
                            content = response_data['choices'][0]['message'].get('content', '')
                            print(content)
                        else:
                            log("Unexpected response format in final reply", "error", args)
                    except json.JSONDecodeError:
                        log(f"Error parsing final response: {response.text}", "error", args)
                
                print("\n")
                print(f"{Style.BRIGHT}{Fore.CYAN}Conversation completed.{Style.RESET_ALL}")
            else:
                log(f"Unknown function: {function_name}", "error", args)
        except json.JSONDecodeError:
            log(f"Error parsing function arguments: {function_args}", "error", args)
        except Exception as e:
            log(f"Error executing function: {str(e)}", "error", args)
    else:
        print("\n")
        print(f"{Style.BRIGHT}{Fore.YELLOW}No function call was detected in the response.{Style.RESET_ALL}")
        print(f"{Style.BRIGHT}Possible reasons:{Style.RESET_ALL}")
        print("1. The model may not support function calling or tool use")
        print("2. The Gnosis proxy may not be properly forwarding the tools parameter")
        print("3. Try running with --debug to see the raw API response")
        print(f"{Style.BRIGHT}{Fore.CYAN}Conversation completed.{Style.RESET_ALL}")

def log(message, level="info", args=None):
    """Log a message with the appropriate color based on level."""
    if not args or (level == "info" and not args.verbose and not args.debug):
        return
        
    if level == "debug" and not args.debug:
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
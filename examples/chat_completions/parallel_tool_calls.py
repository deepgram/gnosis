#!/usr/bin/env python3
import json
import requests
import argparse
import colorama
import time
from colorama import Fore, Style
from concurrent.futures import ThreadPoolExecutor

# Initialize colorama for cross-platform color support
colorama.init()

def main():
    parser = argparse.ArgumentParser(description="Parallel Tool Calling Test for Gnosis")
    parser.add_argument("--host", default="http://localhost:8080", help="Base URL of the Gnosis API")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use")
    parser.add_argument("--system", 
                       default="""
You are a helpful assistant with access to both built-in tools and user-defined tools.
You can use built-in tool calls to find information in our documentation.
You can also use two user-defined tools:
1. get_weather - Gets the current weather for a location
2. calculate - Performs a mathematical calculation

When you need information from multiple sources, you should make tool calls in parallel.
                       """,
                       help="System message")
    parser.add_argument("--user", 
                       default="I need to know about Deepgram's Nova-2 model features, the weather in San Francisco, and what is 123 * 456?",
                       help="User message")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()
    
    endpoint = f"{args.host}/v1/chat/completions"
    
    # Print header
    print(f"{Style.BRIGHT}{Fore.CYAN}Parallel Tool Calling Test Example{Style.RESET_ALL}")
    print("═════════════════════════════════════════")
    print(f"{Style.BRIGHT}Model:{Style.RESET_ALL} {args.model}")
    print(f"{Style.BRIGHT}Host:{Style.RESET_ALL} {args.host}")
    print("═════════════════════════════════════════")
    
    # Define user tools
    user_tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA"
                        }
                    },
                    "required": ["location"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Perform a mathematical calculation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "The mathematical expression to evaluate"
                        }
                    },
                    "required": ["expression"]
                }
            }
        }
    ]
    
    # Prepare the request
    request_data = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": args.system},
            {"role": "user", "content": args.user}
        ],
        "stream": False,  # We don't want streaming for this example
        "temperature": 0.7,
        "max_tokens": 2048,
        "tools": user_tools,  # Add our user-defined tools
        "tool_choice": "auto"  # Enable automatic tool calling
    }
    
    if args.verbose:
        print(f"{Fore.CYAN}[VERBOSE]{Style.RESET_ALL} Request data:")
        print(json.dumps(request_data, indent=2))
    
    log("Sending chat completion request...", "important", args.verbose)
    print(f"\n{Style.BRIGHT}User:{Style.RESET_ALL} {args.user}\n")
    
    # Send the initial request
    response = requests.post(
        endpoint,
        json=request_data,
        headers={"Content-Type": "application/json"}
    )
    
    if args.verbose:
        log(f"Response status: {response.status_code}", "info", args.verbose)
    
    try:
        response_data = response.json()
        
        if args.verbose:
            log("Full initial response:", "debug", args.verbose)
            print(json.dumps(response_data, indent=2))
        
        # Check for gnosis_metadata to show what happened on the server
        if "gnosis_metadata" in response_data:
            metadata = response_data["gnosis_metadata"]
            log("Gnosis metadata received:", "info", args.verbose)
            
            # Display operations that were performed on the server
            if "operations" in metadata:
                operations = metadata["operations"]
                for op in operations:
                    op_type = op.get("operation_type", "unknown")
                    op_name = op.get("name", "unknown")
                    log(f"Server operation: {op_type} - {op_name}", "info", True)
        
        # Check for tool calls in the response
        if 'choices' in response_data and len(response_data['choices']) > 0:
            message = response_data['choices'][0]['message']
            
            if 'tool_calls' in message:
                tool_calls = message['tool_calls']
                log(f"Found {len(tool_calls)} tool calls in response", "important", True)
                
                # Process user-defined tool calls in parallel using ThreadPoolExecutor
                if tool_calls:
                    log(f"Processing {len(tool_calls)} user-defined tool calls in parallel", "important", True)
                    
                    # Define a function to process a single tool call
                    def process_tool_call(tool_call):
                        tool_id = tool_call["id"]
                        function_name = tool_call["function"]["name"]
                        function_args = json.loads(tool_call["function"]["arguments"])
                        
                        # Simulate executing user-defined tools
                        log(f"Executing user tool: {function_name}", "info", True)
                        result = simulate_user_tool_execution(function_name, function_args)
                        
                        return {
                            "tool_call_id": tool_id,
                            "result": result
                        }
                    
                    # Execute all user-defined tool calls in parallel
                    start_time = time.time()
                    with ThreadPoolExecutor(max_workers=len(tool_calls)) as executor:
                        user_results = list(executor.map(process_tool_call, tool_calls))
                    
                    execution_time = (time.time() - start_time) * 1000
                    log(f"Executed {len(user_results)} user tool calls in {execution_time:.2f}ms", "important", True)
                    
                    # Prepare the follow-up request
                    # Start with the original messages
                    next_messages = request_data["messages"].copy()
                    
                    # Add the assistant's message with tool calls
                    next_messages.append(message)
                    
                    # Add the user tool results to the messages
                    for result_obj in user_results:
                        tool_id = result_obj["tool_call_id"]
                        result = result_obj["result"]
                        
                        # Add the tool result message
                        next_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": json.dumps(result)
                        })
                    
                    # Create a follow-up request with the tool results
                    follow_up_request = {
                        "model": args.model,
                        "messages": next_messages,
                        "stream": False,
                        "temperature": 0.7,
                        "max_tokens": 2048
                    }
                    
                    if args.verbose:
                        log("Sending follow-up request with tool results:", "info", True)
                        print(json.dumps(follow_up_request, indent=2))
                    
                    # Send the follow-up request
                    follow_up_response = requests.post(
                        endpoint,
                        json=follow_up_request,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    follow_up_data = follow_up_response.json()
                    
                    if args.verbose:
                        log("Follow-up response:", "debug", True)
                        print(json.dumps(follow_up_data, indent=2))
                    
                    # Print the final response
                    if 'choices' in follow_up_data and len(follow_up_data['choices']) > 0:
                        final_content = follow_up_data['choices'][0]['message'].get('content', '')
                        print(f"{Style.BRIGHT}{Fore.GREEN}Assistant:{Style.RESET_ALL} {final_content}")
                        
                        # Check if there are still tool calls in the response
                        if 'tool_calls' in follow_up_data['choices'][0]['message']:
                            log("Warning: There are still tool calls in the final response", "important", True)
                else:
                    log("No tool calls to process", "info", True)
            else:
                # No tool calls, just print the response
                content = message.get('content', '')
                print(f"{Style.BRIGHT}{Fore.GREEN}Assistant:{Style.RESET_ALL} {content}")
        else:
            log("Unexpected response format", "error", args.verbose)
            print(json.dumps(response_data, indent=2))
    except json.JSONDecodeError:
        log(f"Error parsing response: {response.text}", "error", args.verbose)
        print(response.text)
    
    print("\n")
    log("Request completed.", "important", args.verbose)

def simulate_user_tool_execution(function_name, args):
    """Simulate executing a user-defined tool."""
    log(f"Simulating execution of user tool: {function_name} with args: {args}", "info", True)
    
    # Add a small delay to simulate tool execution time
    time.sleep(1)
    
    if function_name == "get_weather":
        location = args.get("location", "Unknown")
        return {
            "temperature": 72,
            "condition": "Sunny",
            "location": location,
            "humidity": "65%",
            "wind": "10 mph"
        }
    elif function_name == "calculate":
        expression = args.get("expression", "")
        try:
            # WARNING: eval is unsafe in production, this is just for demonstration
            result = eval(expression)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}
    else:
        return {"error": f"Unknown function: {function_name}"}

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
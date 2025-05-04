#!/usr/bin/env python3
import argparse
import json
import time
import requests
from typing import Dict, Any, List
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def setup_colored_logging():
    """Add colors to log levels"""
    try:
        import coloredlogs
        coloredlogs.install(
            level=logging.INFO,
            logger=logger,
            fmt="[%(levelname)s] %(message)s"
        )
    except ImportError:
        pass  # If coloredlogs isn't available, just use regular logging

def parse_args():
    parser = argparse.ArgumentParser(description="Test conversation continuation RAG skipping")
    parser.add_argument("--host", default="http://localhost:8080", help="API host")
    parser.add_argument("--model", default="gpt-4o", help="Model to use")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args()

def print_header(model, host):
    print("Conversation Continuation RAG Test")
    print("═" * 41)
    print(f"Model: {model}")
    print(f"Host: {host}")
    print("═" * 41)

def send_chat_completion_request(host: str, model: str, messages: List[Dict[str, Any]], verbose: bool = False) -> Dict[str, Any]:
    """Send a request to the chat completions API"""
    url = f"{host}/v1/chat/completions"
    
    data = {
        "model": model,
        "messages": messages,
        "stream": False,
        "temperature": 0.7,
        "max_tokens": 2048
    }
    
    if verbose:
        logger.info("[VERBOSE] Request data:")
        print(json.dumps(data, indent=2))

    logger.info("[IMPORTANT] Sending chat completion request...")
    start_time = time.time()
    
    response = requests.post(url, json=data)
    
    duration_ms = (time.time() - start_time) * 1000
    logger.info(f"[INFO] Response status: {response.status_code}")
    logger.info(f"[INFO] Request duration: {duration_ms:.2f}ms")
    
    if response.status_code == 200:
        response_data = response.json()
        
        if verbose:
            logger.info("[DEBUG] Full response:")
            print(json.dumps(response_data, indent=2))
            
        # Log gnosis metadata if available
        if "gnosis_metadata" in response_data:
            logger.info("[INFO] Gnosis metadata received:")
            for op in response_data["gnosis_metadata"].get("operations", []):
                op_type = op.get("operation_type", "unknown")
                op_name = op.get("name", "unknown")
                logger.info(f"[INFO] Server operation: {op_type} - {op_name}")
                
        # Extract the assistant's response
        if "choices" in response_data and len(response_data["choices"]) > 0:
            assistant_message = response_data["choices"][0]["message"]
            return assistant_message
    else:
        logger.error(f"[ERROR] Request failed with status {response.status_code}")
        logger.error(f"[ERROR] Response: {response.text}")
        
    return {}

def main():
    args = parse_args()
    setup_colored_logging()
    print_header(args.model, args.host)
    
    # First message in conversation
    logger.info("[IMPORTANT] SENDING FIRST MESSAGE (should perform RAG)")
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant with expertise in artificial intelligence and machine learning."
        },
        {
            "role": "user",
            "content": "Tell me about Deepgram's Nova-2 model."
        }
    ]
    
    # First response should include RAG
    assistant_message = send_chat_completion_request(args.host, args.model, messages, args.verbose)
    
    # Print the assistant's response
    if "content" in assistant_message:
        print("\nUser: Tell me about Deepgram's Nova-2 model.\n")
        print(f"Assistant: {assistant_message['content']}\n")
    
    # Add the assistant's response to the messages
    messages.append(assistant_message)
    
    # Continue the conversation (this should skip RAG)
    logger.info("\n[IMPORTANT] SENDING FOLLOW-UP MESSAGE (should skip RAG)")
    
    # Add a follow-up user message
    messages.append({
        "role": "user",
        "content": "How does it compare to the previous Nova-1 model?"
    })
    
    # Send the follow-up request
    time.sleep(1)  # Small delay for readability in logs
    follow_up_message = send_chat_completion_request(args.host, args.model, messages, args.verbose)
    
    # Print the follow-up response
    if "content" in follow_up_message:
        print("\nUser: How does it compare to the previous Nova-1 model?\n")
        print(f"Assistant: {follow_up_message['content']}")
    
    print("\n[IMPORTANT] Test completed.")

if __name__ == "__main__":
    main() 
"""
Bread SDK - Chat with Your Baked Model

Before running this script:
1. Install dependencies: pip install -r requirements.txt
2. Set your API key: export BREAD_API_KEY='your_api_key_here'
   - Windows CMD: setx BREAD_API_KEY "your_api_key_here"
   - Windows PowerShell: $env:BREAD_API_KEY='your_api_key_here'
3. Configure MODEL_NAME below to your baked model path
"""

import os
import json
import requests
import dotenv

dotenv.load_dotenv()

# ============ CONFIGURATION ============
BREAD_API_KEY = os.environ.get("BREAD_API_KEY")
# Format: username/repo_name/bake_name/checkpoint or base_model_name
MODEL_NAME = "johndoe/yoda_repo/yoda_bake/21"
BASE_URL = "http://bapi.bread.com.ai/v1/chat/completions"
# Set to True to enable Qwen's thinking mode
ENABLE_THINKING = False
# =======================================

def chat_with_model():
    """Start an interactive chat session with your baked model."""
    
    # Validate configuration
    if not BREAD_API_KEY:
        print("Please set your BREAD_API_KEY environment variable")
        print("export BREAD_API_KEY='your_api_key_here'")
        return
    
    # Initialize conversation history
    conversation_history = []
    
    print("=" * 60)
    print(f"🍞 Bread AI - Chat with Model: {MODEL_NAME.upper()}")
    print("=" * 60)
    print("Type your message and press Enter to chat.")
    print("Type 'exit', 'quit', or 'q' to end the conversation.")
    print("=" * 60)
    print()
    
    while True:
        # Get user input
        user_input = input("YOU: ").strip()
        
        # Check for exit commands
        if user_input.lower() in ['exit', 'quit', 'q']:
            print("\n👋 Goodbye!")
            break
        
        # Skip empty inputs
        if not user_input:
            continue
        
        # Add user message to history
        conversation_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Prepare API request
        headers = {
            "Authorization": f"Bearer {BREAD_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": MODEL_NAME,
            "messages": conversation_history,
            "temperature": 0.7,
            "stream": True
        }
        
        # Add thinking mode configuration for Qwen models
        if not ENABLE_THINKING:
            payload["extra_body"] = {
                "chat_template_kwargs": {
                    "enable_thinking": False
                }
            }
        
        try:
            # Make streaming API request
            response = requests.post(BASE_URL, headers=headers, json=payload, stream=True)
            response.raise_for_status()
            
            # Display streaming response
            print(f"\n{MODEL_NAME.split('/')[-1].upper()}: ", end="", flush=True)
            
            assistant_message = ""
            
            # Process streaming chunks
            for line in response.iter_lines():
                if not line:
                    continue
                    
                line = line.decode('utf-8')
                
                # Skip empty lines and check for stream end
                if line.strip() == "data: [DONE]":
                    break
                
                # Parse SSE format (lines start with "data: ")
                if line.startswith("data: "):
                    try:
                        chunk_data = json.loads(line[6:])  # Remove "data: " prefix
                        delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        
                        if content:
                            print(content, end="", flush=True)
                            assistant_message += content
                    except json.JSONDecodeError:
                        continue
            
            print("\n")  # New line after streaming completes
            
            # Add assistant response to history
            conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            
        except requests.exceptions.HTTPError as e:
            print(f"\nAPI Error: {e}")
            print(f"Response: {response.text}\n")
            # Remove the last user message since we got an error
            conversation_history.pop()
            
        except Exception as e:
            print(f"\nError: {e}\n")
            # Remove the last user message since we got an error
            conversation_history.pop()


if __name__ == "__main__":
    chat_with_model()


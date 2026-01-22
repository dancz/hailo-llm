
import requests
import json
import time

API_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5"

def generate(prompt, context=None):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False # Use non-stream for simplicity in test
    }
    if context:
        payload["context"] = context
        
    start_t = time.time()
    resp = requests.post(API_URL, json=payload)
    dur = time.time() - start_t
    
    if resp.status_code != 200:
        print(f"Error: {resp.text}")
        return None, None, dur
        
    data = resp.json()
    return data['response'], data.get('context'), dur

def run_test():
    print("--- Testing Stateful /api/generate ---")
    
    # 1. Initial Prompt (No context)
    prompt1 = "Hi, my name is Bob."
    print(f"\nUser: {prompt1}")
    output1, context1, dur1 = generate(prompt1)
    print(f"Assistant: {output1.strip()}")
    print(f"Context ID received: {context1}")
    print(f"Latency: {dur1:.2f}s")
    
    if not context1:
        print("FAILURE: No context returned.")
        return

    # 2. Follow-up (With Context, WITHOUT History)
    # Note: We do NOT send "Hi my name is Bob" again. just the new question.
    prompt2 = " What is my name?"
    print(f"\nUser: {prompt2} (sending context={context1})")
    output2, context2, dur2 = generate(prompt2, context=context1)
    print(f"Assistant: {output2.strip()}")
    print(f"Context ID received: {context2}")
    print(f"Latency: {dur2:.2f}s")
    
    if "Bob" in output2:
        print("SUCCESS: Memory preserved!")
    else:
        print("FAILURE: Memory lost.")
        
    # 3. Third Turn (Chain)
    prompt3 = " Tell me a joke."
    print(f"\nUser: {prompt3} (sending context={context2})")
    output3, context3, dur3 = generate(prompt3, context=context2)
    print(f"Assistant: {output3.strip()}")
    print(f"Latency: {dur3:.2f}s")

if __name__ == "__main__":
    run_test()

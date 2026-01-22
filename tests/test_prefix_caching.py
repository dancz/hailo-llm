
import asyncio
import sys
import os
import time

# Ensure app is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.engine.hailo_runner import HailoRunner

async def run_test():
    print("Initializing HailoRunner...")
    runner = HailoRunner()
    model_path = "/home/pi/src/hailoLlm/models"
    
    try:
        runner.load_model(model_path)
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    # Scenario:
    # 1. User sends Prompt A. (Miss) -> Generates, Saves Context A'
    # 2. User sends Prompt A + New Q. (Hit) -> Loads Context A', Generates.
    
    prompt_part1 = "Tell me a joke about a cat."
    
    print("\n--- Step 1: Initial Request (Cache Miss Expected) ---")
    start_time = time.time()
    response1 = ""
    async for token in runner.generate_token_stream(prompt_part1, max_new_tokens=20):
        response1 += token
    time1 = time.time() - start_time
    print(f"Response 1: {response1.strip()}")
    print(f"Time 1: {time1:.4f}s")
    
    # Check cache stats
    stats = runner.context_manager.get_stats()
    print(f"Cache Stats: {stats}")
    if stats['entries'] == 0:
        print("FAILURE: Cache should have 1 entry.")
    else:
        print("SUCCESS: Cache populated.")

    # Construct the full history for the next turn
    # Note: simple concatenation logic used in runner: new_full_history = prompt + full_generated_text
    previous_history = prompt_part1 + response1
    prompt_part2 = previous_history + "\nAnd now a dog."
    
    print("\n--- Step 2: Follow-up Request (Cache Hit Expected) ---")
    start_time = time.time()
    response2 = ""
    async for token in runner.generate_token_stream(prompt_part2, max_new_tokens=20):
        response2 += token
    time2 = time.time() - start_time
    print(f"Response 2: {response2.strip()}")
    print(f"Time 2: {time2:.4f}s")
    
    # If caching works, the prefill time for the "previous_history" part should be near zero.
    # Since prompt_part1 is short, difference might be small.
    # But we can verify functionally.
    
    # Let's try a LONG prompt to see speedup.
    long_prefix = "The quick brown fox jumps over the lazy dog. " * 50
    print(f"\n--- Step 3: Long Prompt Initial (Cache Miss) Length: {len(long_prefix)} ---")
    start_time = time.time()
    resp3 = ""
    async for token in runner.generate_token_stream(long_prefix, max_new_tokens=5):
        resp3 += token
    time3 = time.time() - start_time
    print(f"Time 3: {time3:.4f}s")
    
    full_history_long = long_prefix + resp3
    prompt_long_next = full_history_long + " What matches this?"
    
    print(f"\n--- Step 4: Long Prompt Follow-up (Cache Hit Expected) ---")
    start_time = time.time()
    resp4 = ""
    async for token in runner.generate_token_stream(prompt_long_next, max_new_tokens=5):
        resp4 += token
    time4 = time.time() - start_time
    print(f"Time 4: {time4:.4f}s")
    
    if time4 < time3:
        print(f"SUCCESS: Cache Hit is faster ({time4:.2f}s vs {time3:.2f}s)")
    else:
        print(f"WARNING: Cache Hit was same or slower??")

if __name__ == "__main__":
    asyncio.run(run_test())

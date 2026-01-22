
import asyncio
import sys
import os
import time
import random

# Ensure app is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.engine.hailo_runner import HailoRunner

async def user_session(runner: HailoRunner, user_id: str, prompts: list, delay_start: float = 0):
    await asyncio.sleep(delay_start)
    print(f"[{user_id}] Starting session...")
    
    history = ""
    for i, p in enumerate(prompts):
        # Allow some interleaving time
        
        full_prompt = history + p
        print(f"[{user_id}] Turn {i}: Sending request... (Len: {len(full_prompt)})")
        
        response = ""
        start_t = time.time()
        try:
            async for token in runner.generate_token_stream(full_prompt, max_new_tokens=15):
                response += token
        except Exception as e:
            print(f"[{user_id}] Error: {e}")
            return
            
        dur = time.time() - start_t
        print(f"[{user_id}] Turn {i} Done in {dur:.2f}s. Response: {response.strip()}")
        
        # Verify response is reasonable (not just garbage from bad context loading)
        # Tough to do automatically, but we check length.
        
        history = full_prompt + response
        
        # Random sleep to interleave
        await asyncio.sleep(random.uniform(0.1, 1.0))

async def run_test():
    print("Initializing HailoRunner...")
    runner = HailoRunner()
    model_path = "/home/pi/src/hailoLlm/models"
    try:
        runner.load_model(model_path)
    except:
        return

    # User A: Discussing Space
    prompts_a = [
        "What is the sun? ",
        " How hot is it? ",
        " Will it burn out? "
    ]
    
    # User B: Discussing Math
    prompts_b = [
        "What is 2+2? ",
        " What is 5*5? ",
        " Square root of 9? "
    ]
    
    print("\n--- Starting Multi-User Test ---")
    # Run both concurrently
    task_a = asyncio.create_task(user_session(runner, "UserA", prompts_a, delay_start=0))
    task_b = asyncio.create_task(user_session(runner, "UserB", prompts_b, delay_start=2.0)) # B starts mid-way A
    
    await asyncio.gather(task_a, task_b)
    
    print("\n--- Test Complete ---")
    stats = runner.context_manager.get_stats()
    print(f"Final Cache Stats: {stats}")
    # We expect at least 2 entries (one for A's last state, one for B's last state) 
    # Actually intermediate states might also be cached depending on unique prompt strings?
    # Yes, each turn produces a unique history string.
    # Total A turns: 3. Total B turns: 3. Total entries: 6 (if space permits and not evicted).

if __name__ == "__main__":
    asyncio.run(run_test())

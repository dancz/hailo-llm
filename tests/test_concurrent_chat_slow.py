
import asyncio
import sys
import os
import time
import random

# Ensure app is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.engine.hailo_runner import HailoRunner

async def user_session(runner: HailoRunner, user_id: str, topic: str, turns: int):
    print(f"[{user_id}] Joining chat. Topic: {topic}")
    history = ""
    
    # Simulate a conversation
    questions = [
        f"Lets talk about {topic}. Start with a fact.",
        "Tell me more.",
        "Why is that interesting?",
        "Give me another example.",
        "Summarize what we discussed."
    ]
    
    for i in range(turns):
        if i >= len(questions): break
        
        question = questions[i]
        
        # Simulate "thinking/typing" time - significantly long to allow other user to jump in
        think_time = random.uniform(2.0, 5.0)
        print(f"[{user_id}] Thinking for {think_time:.1f}s...")
        await asyncio.sleep(think_time)
        
        full_prompt = history + f"User: {question}\nAssistant:"
        print(f"[{user_id}] Sending: '{question}'")
        
        response_text = ""
        start_t = time.time()
        try:
            # We use the runner directly. In a real app, this runs on the server.
            # The lock in runner handles the concurrency.
            async for token in runner.generate_token_stream(full_prompt, max_new_tokens=30):
                response_text += token
        except Exception as e:
            print(f"[{user_id}] Error: {e}")
            return
            
        dur = time.time() - start_t
        print(f"[{user_id}] Received ({dur:.2f}s): {response_text.strip()[:50]}...")
        
        # Update history for next turn (Stateless API requirement)
        history = full_prompt + response_text + "\n"

async def run_test():
    print("--- Simulating Slow Concurrent usage ---")
    print("Initializing Engine...")
    runner = HailoRunner()
    try:
        runner.load_model("/home/pi/src/hailoLlm/models")
    except Exception as e:
        print(f"Failed to load: {e}")
        return

    # Two users with distinct topics
    # We expect the runner to swap contexts between them using the Prefix Cache.
    # Because there is a sleep between turns, the lock will be released, allowing the other user to grab it.
    
    task1 = asyncio.create_task(user_session(runner, "Alice", "The Ocean", turns=4))
    task2 = asyncio.create_task(user_session(runner, "Bob",   "Quantum Physics", turns=4))
    
    await asyncio.gather(task1, task2)
    
    print("\n--- Simulation Complete ---")
    stats = runner.context_manager.get_stats()
    print(f"Cache Stats: {stats}")
    print("Note: If 'entries' >= 2, the system successfully cached independent contexts.")

if __name__ == "__main__":
    asyncio.run(run_test())

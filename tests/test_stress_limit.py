
import asyncio
import sys
import os
import time
import random

# Ensure app is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.engine.hailo_runner import HailoRunner

# Configuration
NUM_CHAT_USERS = 5
TURNS_PER_USER = 30
ARTICLE_APP_DELAY = 15.0 # Seconds to wait before starting Article App (let chats warm up)
ARTICLE_QUIZ_DELAY = 30.0 # Seconds to wait after article before asking for quiz

async def chat_user_session(runner: HailoRunner, user_id: str, topic: str):
    print(f"[{user_id}] Joining chat. Topic: {topic}")
    history = ""
    
    for i in range(TURNS_PER_USER):
        # Semi-realistic questions
        question = f"Turn {i}: Tell me a short fact about {topic}."
        
        # Random sleep to interleave
        await asyncio.sleep(random.uniform(1.0, 5.0))
        
        full_prompt = history + f"User: {question}\nAssistant:"
        # print(f"[{user_id}] Sending Turn {i}...")
        
        response_text = ""
        start_t = time.time()
        try:
            async for token in runner.generate_token_stream(full_prompt, max_new_tokens=20):
                response_text += token
        except Exception as e:
            print(f"[{user_id}] Error: {e}")
            return
            
        dur = time.time() - start_t
        if i % 5 == 0: # Print only every 5th turn to reduce spam
            print(f"[{user_id}] Turn {i} Done in {dur:.2f}s.")
        
        history = full_prompt + response_text + "\n"

async def article_app_session(runner: HailoRunner):
    await asyncio.sleep(ARTICLE_APP_DELAY)
    print("\n[ArticleApp] Starting Article Generation...")
    
    topic = "The history of the Internet"
    prompt = f"User: Write a detailed 3-paragraph article about {topic}.\nAssistant:"
    
    article_text = ""
    start_t = time.time()
    try:
        # Requesting more tokens for article
        async for token in runner.generate_token_stream(prompt, max_new_tokens=200):
            article_text += token
    except Exception as e:
        print(f"[ArticleApp] Error: {e}")
        return
    
    dur = time.time() - start_t
    print(f"\n[ArticleApp] Article Generated in {dur:.2f}s. Length: {len(article_text)} chars.")
    
    # Context state: prompt + article_text
    history = prompt + article_text + "\n"
    
    print(f"[ArticleApp] Waiting {ARTICLE_QUIZ_DELAY}s before Quiz (expecting cache retention or eviction)...")
    await asyncio.sleep(ARTICLE_QUIZ_DELAY)
    
    print("\n[ArticleApp] Requesting Quiz...")
    quiz_prompt = history + "User: Create a 3-question quiz based on the article above.\nAssistant:"
    
    quiz_text = ""
    start_t = time.time()
    try:
        async for token in runner.generate_token_stream(quiz_prompt, max_new_tokens=100):
            quiz_text += token
    except Exception as e:
        print(f"[ArticleApp] Error: {e}")
        return
        
    dur = time.time() - start_t
    print(f"\n[ArticleApp] Quiz Generated in {dur:.2f}s.")
    print(f"[ArticleApp] Quiz Content:\n{quiz_text.strip()}\n")

async def run_stress_test():
    print(f"--- Stress Test: {NUM_CHAT_USERS} Users ({TURNS_PER_USER} turns) + 1 Article App ---")
    print("Initializing Engine...")
    runner = HailoRunner()
    
    # Increase cache slightly for the test? Or keep default to TEST LIMITS?
    # User asked to "test the limits". We keep default 400MB.
    # We might see eviction. 
    
    try:
        runner.load_model("/home/pi/src/hailoLlm/models")
    except Exception as e:
        print(f"Failed to load: {e}")
        return
        
    topics = ["Cars", "Music", "History", "Coding", "Cooking"]
    
    tasks = []
    # Create Chat Users
    for i in range(NUM_CHAT_USERS):
        tasks.append(asyncio.create_task(chat_user_session(runner, f"User{i+1}", topics[i % len(topics)])))
        
    # Create Article App
    tasks.append(asyncio.create_task(article_app_session(runner)))
    
    start_all = time.time()
    await asyncio.gather(*tasks)
    total_dur = time.time() - start_all
    
    print(f"\n--- Stress Test Complete in {total_dur:.2f}s ---")
    stats = runner.context_manager.get_stats()
    print(f"Final Cache Stats: {stats}")
    print(f"Total Entries: {stats['entries']}")
    print(f"Total Size: {stats['size_mb']:.2f} MB")
    print(f"Total Evictions: {stats['evictions']}")
    print(f"Total Hits: {runner.cache_hits}")
    print(f"Total Misses: {runner.cache_misses}")
    
    total_ops = runner.cache_hits + runner.cache_misses
    if total_ops > 0:
        print(f"Hit Rate: {runner.cache_hits / total_ops * 100:.1f}%")
        
    print("\n[Analysis]")
    if stats['evictions'] > 0:
        print(f"Confirmed: {stats['evictions']} context(s) were evicted due to size limits.")
    else:
        print("Note: Cache size was sufficient; no evictions occurred.")
        
    # Heuristic for "Lost Context" check
    # Ideally, we'd know if a 'Miss' happened on a turn > 0.
    # But simple Stats summary satisfies user request.
    
    # Interpretation
    if stats['size_mb'] > 300:
        print("Note: Cache is nearly full.")

if __name__ == "__main__":
    asyncio.run(run_stress_test())

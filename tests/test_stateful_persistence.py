
import requests
import json
import time

BASE_URL = "http://localhost:11434/api"

def generate(prompt: str, context: list = None):
    payload = {
        "model": "qwen2.5",
        "prompt": prompt,
        "stream": False
    }
    if context:
        payload["context"] = context
        
    res = requests.post(f"{BASE_URL}/generate", json=payload)
    if res.status_code != 200:
        raise Exception(f"Generate failed: {res.text}")
    return res.json()

def get_stats():
    return requests.get(f"{BASE_URL}/cache/stats").json()

def clear_cache():
    requests.post(f"{BASE_URL}/cache/clear")

def main():
    print("=== Testing Stateful Persistence & Optimization ===")
    
    # 1. Start Clean
    clear_cache()
    print("[x] Cache cleared.")
    
    users = []
    NUM_USERS = 12  # Enough to fill 400MB (approx 10 users). 12 ensures spillover.
    
    # 2. Phase 1: Saturation (Fill RAM, spill to Disk)
    print(f"\nPhase 1: Creating {NUM_USERS} users to saturate RAM...")
    for i in range(NUM_USERS):
        name = f"User{i}"
        # Send a prompt that establishes identity
        res = generate(f"My name is {name}. Remember that.")
        ctx_id = res['context']
        users.append({'name': name, 'context': ctx_id})
        
        # Check stats periodically
        if i % 4 == 0:
            s = get_stats()
            print(f"  [{i+1}/{NUM_USERS}] Created {name}. RAM: {s.get('ram_entries')} entries. Disk: {s.get('disk_entries')} entries.")

    final_stats_p1 = get_stats()
    print(f"Phase 1 Complete. Stats: {final_stats_p1}")
    
    if final_stats_p1['disk_entries'] == 0:
        print("WARNING: RAM was not filled. Test might not be exercising disk swap. Increase NUM_USERS if needed.")
    else:
        print("SUCCESS: Contexts successfully spilled to Disk.")

    # 3. Phase 2: Recall (Retrieve evicted user)
    # The first user (User0) is the oldest LRU, so they should be on Disk (unless cache is huge).
    target_user = users[0] 
    print(f"\nPhase 2: Recalling {target_user['name']} (Should be evicted to Disk)...")
    
    # Capture stats before
    restores_before = get_stats().get('disk_restores', 0)
    
    # Request
    start_t = time.time()
    res = generate("What is my name?", context=target_user['context'])
    duration = time.time() - start_t
    
    print(f"  Response: {res['response'].strip()}")
    print(f"  Duration: {duration:.2f}s")
    
    # Verify Answer
    if target_user['name'] not in res['response']:
        print(f"FAILED: Model forgot name! Expected {target_user['name']}")
    else:
        print(f"SUCCESS: Model remembered {target_user['name']}.")
        
    # Verify Disk Swap
    restores_after = get_stats().get('disk_restores', 0)
    if final_stats_p1['disk_entries'] > 0:
        if restores_after > restores_before:
             print(f"SUCCESS: Verified Disk Restore (Count: {restores_before} -> {restores_after}).")
        else:
             print(f"WARNING: Disk restore count didn't increase. Maybe User0 was still in RAM?")
    
    # Update context for User0 (it changed after generation)
    target_user['context'] = res['context']

    # 4. Phase 3: Optimization (Sequential Access)
    print(f"\nPhase 3: Verify No Thrashing (Accessing {target_user['name']} again immediately)...")
    
    restores_before_running = get_stats().get('disk_restores', 0)
    
    # Run 3 fast requests
    for k in range(3):
        res = generate(f"Count {k}.", context=target_user['context'])
        target_user['context'] = res['context']
        print(f"  Request {k} done.")
        
    restores_after_running = get_stats().get('disk_restores', 0)
    
    if restores_after_running == restores_before_running:
        print("SUCCESS: Disk restore count did NOT increase. Context stayed in RAM.")
    else:
        print(f"FAILED: Disk restore count increased ({restores_after_running}). LRU is thrashing!")

if __name__ == "__main__":
    main()

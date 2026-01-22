
import os
import sys
import time
import asyncio # Not used but good to have
import timeit

try:
    import hailo_platform
    from hailo_platform import VDevice
    import hailo_platform.pyhailort.pyhailort as raw
except ImportError:
    print("Error: hailo_platform not found.")
    sys.exit(1)

MODEL_PATH = "/home/pi/src/hailoLlm/models/Qwen2.5-1.5B-Instruct.hef"

def run_benchmark():
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model file not found at {MODEL_PATH}")
        return

    print("Creating VDevice...")
    vdevice = VDevice()
    print(f"Initializing LLM...")
    llm = raw.LLM(vdevice, MODEL_PATH)

    # 1. Measure Prefill Time for ~500 tokens
    # Generate a long prompt
    long_prompt = "The quick brown fox jumps over the lazy dog. " * 50
    print(f"Long prompt length: {len(long_prompt)} chars")

    print("\n--- Benchmarking Prefill ---")
    start_time = time.time()
    # just generate 1 token to force prefill
    with llm.generate(long_prompt, max_generated_tokens=1) as gen:
        for _ in gen: pass
    prefill_time = time.time() - start_time
    print(f"Prefill time (approx 500 tokens): {prefill_time:.4f}s")

    # 2. Measure Save Context Time
    print("\n--- Benchmarking Save Context ---")
    start_time = time.time()
    context_blob = llm.save_context()
    save_time = time.time() - start_time
    print(f"Save Context time: {save_time:.4f}s")
    print(f"Context Blob size: {len(context_blob) / 1024 / 1024:.2f} MB")

    # 3. Measure Load Context Time
    print("\n--- Benchmarking Load Context ---")
    llm.clear_context()
    start_time = time.time()
    llm.load_context(context_blob)
    load_time = time.time() - start_time
    print(f"Load Context time: {load_time:.4f}s")

    # 4. Measure Generation after Load
    print("\n--- Benchmarking Generation after Load ---")
    new_prompt = " What happened next?"
    start_time = time.time()
    generated_text = ""
    with llm.generate(new_prompt, max_generated_tokens=5) as gen:
        for token in gen: 
            generated_text += token
    gen_time_after_load = time.time() - start_time
    print(f"Generation time (5 tokens) after load: {gen_time_after_load:.4f}s")
    print(f"Output: {generated_text.strip()}")

    # Compare
    print("\n--- Comparison ---")
    print(f"Total Time (Prefill + Gen): {prefill_time + gen_time_after_load:.4f}s (Approx)") # This calculation is illustrative
    print(f"Total Time (Load + Gen):    {load_time + gen_time_after_load:.4f}s")
    
    if load_time < prefill_time:
        print("RESULT: Caching is FASTER.")
    else:
        print("RESULT: Caching is SLOWER.")

if __name__ == "__main__":
    run_benchmark()

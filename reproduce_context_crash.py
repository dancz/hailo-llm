
import os
import sys
import time

try:
    import hailo_platform
    from hailo_platform import VDevice
    import hailo_platform.pyhailort.pyhailort as raw
except ImportError:
    print("Error: hailo_platform not found.")
    sys.exit(1)

MODEL_PATH = "/home/pi/src/hailoLlm/models/Qwen2.5-1.5B-Instruct.hef"

if not os.path.exists(MODEL_PATH):
    print(f"Error: Model file not found at {MODEL_PATH}")
    sys.exit(1)

def run_test():
    print("Creating VDevice...")
    vdevice = VDevice()
    
    print(f"Initializing LLM from {MODEL_PATH}...")
    llm = raw.LLM(vdevice, MODEL_PATH)

    print("Generating part 1 (Context A)...")
    prompt1 = "Describe the sun in one sentence."
    # Consume generator
    full_text1 = ""
    with llm.generate(prompt1, max_generated_tokens=20) as gen:
        for token in gen:
            full_text1 += token
    print(f"Output 1: {full_text1}")

    print("Saving context...")
    try:
        context_blob = llm.save_context()
        print(f"Context saved. Size: {len(context_blob)} bytes")
    except Exception as e:
        print(f"Failed to save context: {e}")
        return

    print("Clearing context...")
    llm.clear_context()

    print("Generating part 2 (Context B - unrelated)...")
    prompt2 = "What is 2+2? Answer in one word."
    full_text2 = ""
    with llm.generate(prompt2, max_generated_tokens=10) as gen:
        for token in gen:
            full_text2 += token
    print(f"Output 2: {full_text2}")

    print("Restoring Context A...")
    try:
        llm.load_context(context_blob)
        print("Context loaded.")
    except Exception as e:
        print(f"Failed to load context: {e}")
        return

    print("Generating part 3 (Continuation of Context A)...")
    prompt3 = " and the moon."
    full_text3 = ""
    try:
        # Note: prompt3 is just appended to the restored context?
        # Or does generate() start fresh if we don't say explicitly?
        # LLM state is managed internally. load_context should restore internal KV cache.
        with llm.generate(prompt3, max_generated_tokens=20) as gen:
            for token in gen:
                full_text3 += token
        print(f"Output 3: {full_text3}")
    except Exception as e:
        print(f"Failed to generate after restore: {e}")

if __name__ == "__main__":
    run_test()

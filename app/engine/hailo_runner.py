import os
import time
from typing import Generator
from app.engine.base import BaseRunner

try:
    import hailo_platform
    from hailo_platform import VDevice
    # Import the hidden pyhailort module to access LLM class
    import hailo_platform.pyhailort.pyhailort as raw
    HAILO_AVAILABLE = True
except ImportError:
    HAILO_AVAILABLE = False
    print("Warning: hailo_platform not found. HailoRunner will fail if initialized.")

import asyncio

class HailoRunner(BaseRunner):
    def __init__(self):
        self.model_name = "qwen2.5-hailo"
        self.hef_path = None
        self.vdevice = None
        self.llm = None
        self.lock = asyncio.Lock()
        
    def load_model(self, model_path: str):
        if not HAILO_AVAILABLE:
            raise RuntimeError("Hailo Platform not installed.")
            
        print(f"Loading Hailo model from {model_path}...")
        self.hef_path = os.path.join(model_path, "Qwen2.5-1.5B-Instruct.hef")
        
        # Initialize VDevice
        print("Creating VDevice...")
        self.vdevice = VDevice()
        
        # Initialize LLM
        print(f"Initializing LLM from {self.hef_path}...")
        # Note: raw.LLM expects the high-level VDevice object.
        self.llm = raw.LLM(self.vdevice, self.hef_path)
        
        print("Hailo LLM loaded successfully.")

    async def generate_token_stream(self, prompt: str, max_new_tokens: int = 128, temperature: float = 0.7):
        # We define an async generator for the lock scope
        async with self.lock:
             # Ensure stateless behavior: Clear context from previous user
             # We rely on the fact that 'LLM' class likely has such method, or we use .generate_all if it clears automatically?
             # Based on C++ code, llm.clear_context() was available.
             # inspect_llm showed 'load_context', 'save_context', 'max_context_capacity', 'get_context_usage_size'.
             # It did NOT explicitly show 'clear_context' in the snippet I saw? 
             # Wait, Inspect LLM output from Step 345:
             # "Use ``clear_context()`` to reset the conversation history." -> Yes it exists in docstring!
             try:
                 self.llm.clear_context()
             except AttributeError:
                 # Fallback if method is named differently or missing?
                 print("Warning: clear_context method not found, context mixing might occur.")

             # Run generation in a threadpool if it blocks?
             # The raw.LLM.generate method returns an iterator. Iterating it is blocking C++ call typically.
             # If we block here, we block the asyncio loop.
             # Ideally validation shows if generate() yields quickly.
             
             try:
                # Assuming prompt is sufficient context for this stateless request
                # We do NOT use 'with self.llm.generate(...) as gen' directly because it's not async context manager.
                # But we validly use it inside the async lock.
                # However, the iteration itself `for token in gen` is synchronous. 
                # This will block other coroutines (like heartbeats) but the Lock ensures no other inference runs.
                
                with self.llm.generate(prompt, max_generated_tokens=max_new_tokens, temperature=temperature) as gen:
                    for token in gen:
                        # Give usage info back to loop occasionally?
                        # await asyncio.sleep(0) 
                        yield token
                        await asyncio.sleep(0) # Yield control to event loop to allow other tasks (like accept connection) to progress
             except Exception as e:
                print(f"Generation error: {e}")
                yield f" [Error: {e}]"

    def generate(self, prompt: str, max_new_tokens: int = 128, temperature: float = 0.7) -> Generator[str, None, None]:
        # This synchronous interface is mandated by BaseRunner.
        # But we need async for Locking.
        # This implies we should refactor BaseRunner to be Async or bridge it.
        # Given we are in FastAPI, we can assume the caller `routes.py` can call an async method.
        # I will update BaseRunner to allow async, OR implementing a bridge here is messy.
        # BETTER PLAN: Rename this method to `generate_sync` (broken) or just implement `generate_async`. 
        # And trigger `task_boundary` to update `BaseRunner` definition first.
        pass
                 
    def get_model_name(self) -> str:
        return self.model_name

    def __del__(self):
        # Cleanup
        if self.llm:
            try:
                # self.llm.release() # raw.LLM might not need explicit release if context managed?
                # Help said release() is called automatically with context manager for completion, 
                # but for LLM instance itself?
                pass
            except:
                pass

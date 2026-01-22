import os
import time
from typing import Generator
from app.engine.base import BaseRunner
from app.engine.context_manager import ContextManager

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
        self.context_manager = ContextManager(max_cache_size_mb=400) # Reserve 400MB for context cache
        self.cache_hits = 0
        self.cache_misses = 0
        
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
        async with self.lock:
             # Prefix Caching Logic
             longest_match_text = self.context_manager.find_longest_prefix(prompt)
             
             loaded_from_cache = False
             if longest_match_text:
                 # print(f"DEBUG: Cache Hit! Prefix len: {len(longest_match_text)}")
                 blob = self.context_manager.get_context(longest_match_text)
                 if blob:
                     try:
                         # 1. Clear before load is safer to avoid accumulation errors
                         self.llm.clear_context()
                         self.llm.load_context(blob)
                         loaded_from_cache = True
                         self.cache_hits += 1
                         
                         # Identify the *new* part of the prompt
                         prompt_to_process = prompt[len(longest_match_text):]
                     except Exception as e:
                         print(f"Warning: Failed to load context: {e}")
                         self.llm.clear_context()
                         prompt_to_process = prompt
                 else:
                     prompt_to_process = prompt
             else:
                 prompt_to_process = prompt
                 self.llm.clear_context() # Stateless fallback
                 self.cache_misses += 1
                 
             # Generate
             full_generated_text = ""
             try:
                # If loaded from cache and prompt_to_process is empty, we might just be continuing?
                # But typically prompt_to_process has at least the new user message.
                
                with self.llm.generate(prompt_to_process, max_generated_tokens=max_new_tokens, temperature=temperature) as gen:
                    for token in gen:
                        full_generated_text += token
                        yield token
                        await asyncio.sleep(0)
                        
                # Cache the result for next time!
                # The new state represents: prompt + full_generated_text
                # If we loaded from cache, 'prompt' was (prefix + new_part).
                # So the full sequence is (prompt + full_generated_text).
                new_full_history = prompt + full_generated_text
                
                # Retrieve the blob *now*
                try:
                    new_blob = self.llm.save_context()
                    self.context_manager.cache_context(new_full_history, new_blob)
                except Exception as e:
                    print(f"Warning: Failed to save context: {e}")
                
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

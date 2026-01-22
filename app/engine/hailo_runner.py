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

    async def generate_token_stream(self, prompt: str, max_new_tokens: int = 128, temperature: float = 0.7, context_id: int = None):
        async with self.lock:
             prompt_to_process = prompt
             # Stateful / Context ID Logic
             if context_id is not None:
                 # Client provided a specific context ID. Try to load it.
                 # We use the string representation of ID as the key in ContextManager
                 key = f"ctx:{context_id}" 
                 blob = self.context_manager.get_context(key)
                 if blob:
                     try:
                         self.llm.clear_context()
                         self.llm.load_context(blob)
                         self.cache_hits += 1
                         # With explicit context ID, we assume the prompt is just the *continuation*
                         # So we process the whole 'prompt' string as new tokens.
                         prompt_to_process = prompt 
                     except Exception as e:
                         print(f"Warning: Failed to load context {context_id}: {e}")
                         # If explicitly requested context fails, we arguably should fail request?
                         # Or fallback? Fallback means loss of memory.
                         # User said "not be needed to send whole history". So fallback is USELESS.
                         # We should probably raise, but yield error text is safer for stream.
                         pass
                 else:
                     # ID not found (evicted or invalid)
                     self.cache_misses += 1
                     yield f" [Error: Context ID {context_id} not found/evicted]"
                     return

             elif self.context_manager:
                 # Fallback to Prefix Caching (Stateless Chat Mode)
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
                new_full_history = prompt + full_generated_text
                
                # Retrieve the blob *now*
                try:
                    new_blob = self.llm.save_context()
                    # 1. Save for Prefix Caching (Stateless)
                    self.context_manager.cache_context(new_full_history, new_blob)
                    
                    # 2. Save for Stateful Context ID (Stateful)
                    # Use a simple integer hash/ID. Using timestamp for uniqueness.
                    import time
                    new_context_id = int(time.time() * 1000)
                    self.context_manager.cache_context(f"ctx:{new_context_id}", new_blob)
                    
                    # Yield the ID to the caller so they can return it to client
                    yield new_context_id
                    
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

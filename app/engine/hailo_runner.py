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

class HailoRunner(BaseRunner):
    def __init__(self):
        self.model_name = "qwen2.5-hailo"
        self.hef_path = None
        self.vdevice = None
        self.llm = None
        
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

    def generate(self, prompt: str, max_new_tokens: int = 128, temperature: float = 0.7) -> Generator[str, None, None]:
        if not self.llm:
             raise RuntimeError("Model not loaded.")
        
        # Using the streaming interface
        # Note: prompt is passed directly. 
        # If needed, we could format it with chat template here if API expects raw text.
        # But API also supports list of dicts.
        # BaseRunner passes raw string prompt (formatted by caller).
        
        # max_output_tokens? args might differ slightly from base.
        # verify_llm_class showed: generate(prompt, temperature, max_new_tokens, ...)
        # Actually help showed: generate(self, prompt, ...) and returns completion object
        
        # We need to adapt arguments.
        # help showed: with llm.generate(prompt="...", ...) as gen:
        
        try:
            with self.llm.generate(prompt, max_generated_tokens=max_new_tokens, temperature=temperature) as gen:
                for token in gen:
                    yield token
        except Exception as e:
            print(f"Generation error: {e}")
            yield f" [Error: {e}]"
                 
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

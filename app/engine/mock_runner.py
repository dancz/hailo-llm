import time
import asyncio
import random
from typing import Generator, AsyncGenerator
from app.engine.base import BaseRunner

class MockRunner(BaseRunner):
    def __init__(self):
        self.model_name = "mock-qwen2.5"

    def load_model(self, model_path: str):
        print(f"Loading Mock model from {model_path}...")
        time.sleep(0.1) 
        print("Mock model loaded.")

    def generate(self, prompt: str, max_new_tokens: int = 128, temperature: float = 0.7):
        # Sync fallback
        yield "Sync generate not supported in async mode."

    async def generate_token_stream(self, prompt: str, max_new_tokens: int = 128, temperature: float = 0.7) -> AsyncGenerator[str, None]:
        # Simple mock response logic
        response_text = f" This is a mock response to '{prompt}'. "
        words = response_text.split()
        
        # Add some random filler text to make it longer
        filler = ["The", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog."]
        for _ in range(max_new_tokens // len(filler)):
             words.extend(filler)
        
        for word in words:
            yield word + " "
            await asyncio.sleep(random.uniform(0.01, 0.05)) # Simulate inference latency

    def get_model_name(self) -> str:
        return self.model_name

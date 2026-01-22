from abc import ABC, abstractmethod
from typing import Generator, List, AsyncGenerator

class BaseRunner(ABC):
    @abstractmethod
    def load_model(self, model_path: str):
        """Load the model resources."""
        pass

    # Deprecated sync method
    def generate(self, prompt: str, max_new_tokens: int = 128, temperature: float = 0.7) -> Generator[str, None, None]:
        pass

    @abstractmethod
    async def generate_token_stream(self, prompt: str, max_new_tokens: int = 128, temperature: float = 0.7) -> AsyncGenerator[str, None]:
        """Generate text from a prompt, yielding tokens asynchronously."""
        pass
        
    @abstractmethod
    def get_model_name(self) -> str:
        """Return the name of the loaded model."""
        pass

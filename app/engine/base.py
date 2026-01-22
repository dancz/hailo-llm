from abc import ABC, abstractmethod
from typing import Generator, List

class BaseRunner(ABC):
    @abstractmethod
    def load_model(self, model_path: str):
        """Load the model resources."""
        pass

    @abstractmethod
    def generate(self, prompt: str, max_new_tokens: int = 128, temperature: float = 0.7) -> Generator[str, None, None]:
        """Generate text from a prompt, yielding tokens."""
        pass
        
    @abstractmethod
    def get_model_name(self) -> str:
        """Return the name of the loaded model."""
        pass

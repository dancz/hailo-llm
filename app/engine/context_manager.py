
from typing import Dict, Optional, Tuple, List
from collections import OrderedDict
import time

class ContextManager:
    """
    Manages an LRU cache of LLM context blobs.
    
    Keys are the full prompt history (text string).
    Values are the binary context blobs returned by the Hailo LLM.
    """
    def __init__(self, max_cache_size_mb: int = 400):
        self.cache: OrderedDict[str, bytes] = OrderedDict()
        self.current_size_bytes = 0
        self.max_size_bytes = max_cache_size_mb * 1024 * 1024
        self.eviction_count = 0

        
    def get_context(self, history_text: str) -> Optional[bytes]:
        """
        Retrieve context blob for a given exact history.
        Moves the item to the end (MRU) if found.
        """
        if history_text in self.cache:
            self.cache.move_to_end(history_text)
            return self.cache[history_text]
        return None
    
    def find_longest_prefix(self, current_prompt: str) -> Optional[str]:
        """
        Finds the key in the cache that is the longest prefix of current_prompt.
        Returns the key (text) or None.
        """
        best_key = None
        best_len = 0
        
        # Iterate over all cached keys
        # Since cache is OrderedDict ordered by LRU, iteration order doesn't strictly matter for correctness
        # but we want the *longest* match.
        for key in self.cache.keys():
            if current_prompt.startswith(key):
                if len(key) > best_len:
                    best_len = len(key)
                    best_key = key
                    
        return best_key
    
    def cache_context(self, history_text: str, context_blob: bytes):
        """
        Cache a context blob for a given history.
        Evicts old entries if size limit is exceeded.
        """
        blob_size = len(context_blob)
        
        # If already exists, update key order and size diff
        if history_text in self.cache:
            self.current_size_bytes -= len(self.cache[history_text])
            self.cache.move_to_end(history_text)
        
        self.cache[history_text] = context_blob
        self.current_size_bytes += blob_size
        
        self._enforce_size_limit()
        
    def _enforce_size_limit(self):
        while self.current_size_bytes > self.max_size_bytes and self.cache:
            # Pop first item (LRU)
            key, blob = self.cache.popitem(last=False)
            self.current_size_bytes -= len(blob)
            self.eviction_count += 1
            
    def clear(self):
        self.cache.clear()
        self.current_size_bytes = 0
        self.eviction_count = 0

    def get_stats(self) -> Dict:
        return {
            "entries": len(self.cache),
            "size_mb": self.current_size_bytes / (1024 * 1024),
            "max_mb": self.max_size_bytes / (1024 * 1024),
            "evictions": self.eviction_count
        }

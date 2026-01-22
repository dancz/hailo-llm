
import os
import hashlib
from typing import Dict, Optional, Tuple, List
from collections import OrderedDict
import time
import shutil

class ContextManager:
    """
    Manages a tiered cache (RAM + Disk) of LLM context blobs.
    
    Tier 1 (RAM): Fast, limited size (default 400MB).
    Tier 2 (Disk): Slower, large size (limited by disk space/quota).
    
    Keys are either:
    1. Full prompt history text (Prefix Caching).
    2. "ctx:{id}" strings (Stateful API).
    """
    def __init__(self, max_cache_size_mb: int = 400, disk_cache_dir: str = "cache/contexts", max_disk_size_gb: int = 10):
        self.cache: OrderedDict[str, bytes] = OrderedDict()
        self.current_size_bytes = 0
        self.max_size_bytes = max_cache_size_mb * 1024 * 1024
        
        self.disk_cache_dir = disk_cache_dir
        self.max_disk_size_bytes = max_disk_size_gb * 1024 * 1024 * 1024
        self.eviction_count = 0 
        self.disk_hits = 0
        
        # Ensure disk cache directory exists
        os.makedirs(self.disk_cache_dir, exist_ok=True)
        
    def _get_disk_path(self, key: str) -> str:
        # Use simple hash for filename to handle long keys/special chars
        safe_name = hashlib.sha256(key.encode('utf-8')).hexdigest()
        return os.path.join(self.disk_cache_dir, safe_name + ".bin")

    def get_context(self, key: str) -> Optional[bytes]:
        """
        Retrieve context blob.
        1. Checks RAM.
        2. Checks Disk (if found, promotes to RAM).
        """
        # 1. Check RAM
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
            
        # 2. Check Disk
        disk_path = self._get_disk_path(key)
        if os.path.exists(disk_path):
            try:
                with open(disk_path, "rb") as f:
                    blob = f.read()
                
                # Promote to RAM (This might trigger an eviction back to disk for someone else)
                self.cache_context(key, blob)
                
                # Remove from disk (it's in RAM now)
                os.remove(disk_path)
                
                self.disk_hits += 1
                return blob
            except Exception as e:
                print(f"Error reading context from disk: {e}")
                return None
                
        return None
    
    def find_longest_prefix(self, current_prompt: str) -> Optional[str]:
        """
        Finds the key in the *RAM* cache that is the longest prefix.
        Note: We currently only search RAM for prefixes to avoid expensive disk scans.
        The most active contexts should be in RAM anyway.
        """
        best_key = None
        best_len = 0
        
        for key in self.cache.keys():
            if current_prompt.startswith(key):
                if len(key) > best_len:
                    best_len = len(key)
                    best_key = key
                    
        return best_key
    
    def cache_context(self, key: str, context_blob: bytes):
        """
        Cache a context blob.
        Evicts old entries to DISK if RAM limit is exceeded.
        """
        blob_size = len(context_blob)
        
        # If already exists in RAM, update
        if key in self.cache:
            self.current_size_bytes -= len(self.cache[key])
            self.cache.move_to_end(key)
        
        self.cache[key] = context_blob
        self.current_size_bytes += blob_size
        
        self._enforce_size_limit()
        
    def _enforce_size_limit(self):
        """
        Moves LRU items from RAM to Disk until under limit.
        """
        while self.current_size_bytes > self.max_size_bytes and self.cache:
            # Pop first item (LRU)
            key, blob = self.cache.popitem(last=False)
            self.current_size_bytes -= len(blob)
            
            # Save to Disk
            try:
                disk_path = self._get_disk_path(key)
                with open(disk_path, "wb") as f:
                    f.write(blob)
                self.eviction_count += 1
                
                # Check disk usage after write
                self._enforce_disk_limit()
            except Exception as e:
                print(f"Error saving evicted context to disk: {e}")
                
    def _enforce_disk_limit(self):
        """
        Calculates total disk usage and deletes oldest files if over limit.
        This is an expensive operation (scan dir), so we could optimize to not run every time,
        but for stability we run it on every write to disk.
        """
        try:
            files = []
            total_size = 0
            
            # Scan directory
            with os.scandir(self.disk_cache_dir) as it:
                for entry in it:
                    if entry.is_file():
                        stat = entry.stat()
                        total_size += stat.st_size
                        files.append((entry.path, stat.st_mtime))
            
            # If over limit, start deleting oldest
            if total_size > self.max_disk_size_bytes:
                # Sort by mtime (oldest first)
                files.sort(key=lambda x: x[1])
                
                for path, mtime in files:
                    if total_size <= self.max_disk_size_bytes:
                        break
                    
                    try:
                        size = os.path.getsize(path)
                        os.remove(path)
                        total_size -= size
                    except OSError:
                        pass # File might be gone
        except Exception as e:
            print(f"Error during disk cleanup: {e}")
            
    def clear(self):
        """Clear both RAM and Disk cache"""
        self.cache.clear()
        self.current_size_bytes = 0
        self.eviction_count = 0
        self.disk_hits = 0
        
        # Clear disk directory
        if os.path.exists(self.disk_cache_dir):
            shutil.rmtree(self.disk_cache_dir)
            os.makedirs(self.disk_cache_dir, exist_ok=True)

    def get_stats(self) -> Dict:
        # Count disk files
        disk_files = 0
        disk_usage = 0
        if os.path.exists(self.disk_cache_dir):
             with os.scandir(self.disk_cache_dir) as it:
                for entry in it:
                     if entry.is_file():
                         disk_files += 1
                         disk_usage += entry.stat().st_size

        return {
            "ram_entries": len(self.cache),
            "ram_size_mb": self.current_size_bytes / (1024 * 1024),
            "disk_entries": disk_files,
            "disk_size_mb": disk_usage / (1024 * 1024),
            "disk_limit_mb": self.max_disk_size_bytes / (1024 * 1024),
            "evictions_to_disk": self.eviction_count,
            "disk_restores": self.disk_hits
        }

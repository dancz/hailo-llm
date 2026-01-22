
import unittest
import shutil
import os
import random
import string
from app.engine.context_manager import ContextManager

class TestDiskCache(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_cache_contexts"
        # 2 MB limit (enough for 2 items of 1MB)
        self.mgr = ContextManager(max_cache_size_mb=2, disk_cache_dir=self.test_dir)
        # 1 MB blob
        self.blob_size = 1024 * 1024
        self.blob = b'\x00' * self.blob_size

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_eviction_to_disk(self):
        print("\n--- Testing Eviction to Disk ---")
        
        # 1. Fill RAM (Limit is 2MB aka 2 chunks)
        # Add A
        print("adding A")
        self.mgr.cache_context("key_A", b'A' * self.blob_size)
        # Add B
        print("adding B")
        self.mgr.cache_context("key_B", b'B' * self.blob_size)
        
        stats = self.mgr.get_stats()
        print(f"Stats after A, B: {stats}")
        self.assertEqual(stats['ram_entries'], 2)
        self.assertEqual(stats['disk_entries'], 0) # No evictions yet

        # 2. Overflow RAM -> Evict A (LRU)
        print("adding C (Should evict A)")
        self.mgr.cache_context("key_C", b'C' * self.blob_size)
        
        stats = self.mgr.get_stats()
        print(f"Stats after C: {stats}")
        self.assertEqual(stats['ram_entries'], 2) # B, C
        self.assertEqual(stats['disk_entries'], 1) # A is on disk
        
        # Verify A is clearly evicted
        self.assertNotIn("key_A", self.mgr.cache)
        self.assertIn("key_B", self.mgr.cache)
        self.assertIn("key_C", self.mgr.cache)

    def test_restore_from_disk(self):
        print("\n--- Testing Restore from Disk ---")
        # 1. Fill RAM with A, B
        self.mgr.cache_context("key_A", b'A' * self.blob_size)
        self.mgr.cache_context("key_B", b'B' * self.blob_size)
        
        # 2. Add C -> Evicts A to Disk
        self.mgr.cache_context("key_C", b'C' * self.blob_size)
        
        # 3. Retrieve A (Should come from disk)
        print("Retrieving A (Should be on disk)...")
        blob_a = self.mgr.get_context("key_A")
        
        self.assertIsNotNone(blob_a)
        self.assertEqual(blob_a, b'A' * self.blob_size)
        
        stats = self.mgr.get_stats()
        print(f"Stats after A restore: {stats}")
        
        # A should be back in RAM
        self.assertIn("key_A", self.mgr.cache)
        
        # Likely B was evicted (LRU after C was added? No, order was A(evicted), B, C. 
        # So RAM had [B, C]. Retrieve A -> RAM [C, A] (B evicted).
        # Let's check who is in RAM.
        print(f"Keys in RAM: {list(self.mgr.cache.keys())}")
        
        # Check disk hits
        self.assertEqual(stats['disk_restores'], 1)
        # Check disk entries. A was removed from disk. B should have been evicted.
        # So we should still have 1 file on disk? (B)
        # Check disk entries. A was removed from disk. B should have been evicted.
        # So we should still have 1 file on disk? (B)
        self.assertEqual(stats['disk_entries'], 1) 

    def test_disk_cleanup(self):
        print("\n--- Testing Disk Cleanup (Hard Limit) ---")
        import time 
        
        # Reset with new limits
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            
        # Mock class passing 
        # Since I can't easily patch the class default in this script without import tricks,
        # I'll rely on the constructor argument I added.
        # But wait, max_disk_size_gb expects INT. I cannot pass 0.002.
        # So I will init with 1GB and then manually overwrite the attribute.
        
        mgr = ContextManager(max_cache_size_mb=1, disk_cache_dir=self.test_dir, max_disk_size_gb=1)
        # OVERRIDE bytes manually for fine-grained testing (2MB limit)
        mgr.max_disk_size_bytes = 2 * 1024 * 1024 
        
        self.blob_size = 1024 * 1024
        
        # 1. Fill RAM (A) -> RAM: [A] (1MB)
        print("Adding A")
        mgr.cache_context("key_A", b'A' * self.blob_size)
        
        # 2. Add B -> RAM: [B] (1MB). Evict A to Disk -> Disk: [A] (1MB)
        print("Adding B (Evict A)")
        mgr.cache_context("key_B", b'B' * self.blob_size)
        self.assertEqual(mgr.get_stats()['disk_entries'], 1)
        
        # 3. Add C -> RAM: [C]. Evict B to Disk -> Disk: [A, B] (2MB)
        print("Adding C (Evict B)")
        mgr.cache_context("key_C", b'C' * self.blob_size)
        self.assertEqual(mgr.get_stats()['disk_entries'], 2)
        
        # Sleep to ensure timestamp diff for reliable sorting
        time.sleep(1.1)
        
        # 4. Add D -> RAM: [D]. Evict C to Disk.
        # Disk WAS 2MB. Adding C (1MB) makes it 3MB. Limit is 2MB.
        # Should delete oldest (A). Resulting Disk: [B, C]. Size 2MB.
        print("Adding D (Evict C, Overflow Disk)")
        mgr.cache_context("key_D", b'D' * self.blob_size)
        
        stats = mgr.get_stats()
        print(f"Disk Stats: {stats}")
        
        # Should have 2 entries on disk (B, C)
        self.assertEqual(stats['disk_entries'], 2)
        
        # Verify A is gone (Check via manager)
        # get_context checks RAM (D) then Disk (B, C). A is gone.
        self.assertIsNone(mgr.get_context("key_A"))
        
        # Verify A file is gone
        safe_name_a = mgr._get_disk_path("key_A")
        self.assertFalse(os.path.exists(safe_name_a))

        print("SUCCESS: A was deleted from disk.")

if __name__ == '__main__':
    unittest.main()

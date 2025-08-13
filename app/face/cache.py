"""Thread-safe caching for face encodings"""

import threading
import numpy as np
from typing import Dict, Optional
from .config import AppConfig

class FaceEncodingCache:
    """Thread-safe face encoding cache with size limit"""
    
    def __init__(self, max_size: int = AppConfig.CACHE_SIZE_LIMIT):
        self._cache: Dict[int, np.ndarray] = {}
        self._access_order: List[int] = []
        self._lock = threading.RLock()
        self._max_size = max_size
    
    def get(self, employee_id: int) -> Optional[np.ndarray]:
        """Get encoding from cache"""
        with self._lock:
            if employee_id in self._cache:
                # Move to end (most recently used)
                self._access_order.remove(employee_id)
                self._access_order.append(employee_id)
                return self._cache[employee_id].copy()
            return None
    
    def set(self, employee_id: int, encoding: np.ndarray) -> None:
        """Set encoding in cache with LRU eviction"""
        with self._lock:
            if employee_id in self._cache:
                self._access_order.remove(employee_id)
            elif len(self._cache) >= self._max_size:
                # Remove least recently used
                oldest = self._access_order.pop(0)
                del self._cache[oldest]
            
            self._cache[employee_id] = encoding.copy()
            self._access_order.append(employee_id)
    
    def remove(self, employee_id: int) -> None:
        """Remove encoding from cache"""
        with self._lock:
            if employee_id in self._cache:
                del self._cache[employee_id]
                self._access_order.remove(employee_id)
    
    def clear(self) -> None:
        """Clear all cache"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def __contains__(self, employee_id: int) -> bool:
        with self._lock:
            return employee_id in self._cache
    
    def size(self) -> int:
        """Get current cache size"""
        with self._lock:
            return len(self._cache)

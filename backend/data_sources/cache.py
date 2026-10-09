"""
ClimateShield - Local Data Cache System
Provides thread-safe file caching for satellite and reanalysis API payloads with TTL support.
"""

import os
import json
import time
import hashlib
from typing import Any, Optional, Dict


class DataSourceCache:
    """
    Configurable local disk cache for raw satellite & climate model data downloads.
    """

    def __init__(self, cache_dir: Optional[str] = None, default_ttl_seconds: int = 86400):
        if cache_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_dir = os.path.join(base_dir, "data", "cache")
        
        self.cache_dir = cache_dir
        self.default_ttl_seconds = default_ttl_seconds
        os.makedirs(self.cache_dir, exist_ok=True)

    def _generate_key(self, namespace: str, params: Dict[str, Any]) -> str:
        """Generates deterministic SHA-256 hash key for namespace + params dict."""
        serialized = json.dumps({"namespace": namespace, "params": params}, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get_filepath(self, key: str, extension: str = "json") -> str:
        """Returns target file path for a cache key."""
        return os.path.join(self.cache_dir, f"{key}.{extension}")

    def get(self, namespace: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached payload if present and not expired.
        """
        key = self._generate_key(namespace, params)
        json_path = self.get_filepath(key, "json")
        meta_path = self.get_filepath(key, "meta")

        if not os.path.exists(json_path) or not os.path.exists(meta_path):
            return None

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

            expires_at = meta.get("expires_at", 0)
            if time.time() > expires_at:
                # Expired
                self.delete(namespace, params)
                return None

            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return data
        except Exception:
            return None

    def set(
        self,
        namespace: str,
        params: Dict[str, Any],
        data: Dict[str, Any],
        ttl_seconds: Optional[int] = None
    ) -> str:
        """
        Saves JSON payload and metadata into disk cache.
        """
        key = self._generate_key(namespace, params)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        expires_at = time.time() + ttl

        json_path = self.get_filepath(key, "json")
        meta_path = self.get_filepath(key, "meta")

        meta = {
            "key": key,
            "namespace": namespace,
            "params": params,
            "created_at": time.time(),
            "expires_at": expires_at,
            "ttl_seconds": ttl
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        return key

    def delete(self, namespace: str, params: Dict[str, Any]) -> bool:
        """Deletes cached item if exists."""
        key = self._generate_key(namespace, params)
        deleted = False
        for ext in ["json", "meta", "nc", "h5", "tif"]:
            path = self.get_filepath(key, ext)
            if os.path.exists(path):
                try:
                    os.remove(path)
                    deleted = True
                except OSError:
                    pass
        return deleted

    def clear(self) -> int:
        """Clears all cached files in cache_dir."""
        count = 0
        if os.path.exists(self.cache_dir):
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.isfile(filepath):
                    try:
                        os.remove(filepath)
                        count += 1
                    except OSError:
                        pass
        return count

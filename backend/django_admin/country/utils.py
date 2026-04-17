# country/utils.py
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

def safe_cache_get(key):
    try:
        return cache.get(key)
    except Exception as e:
        logger.warning(f"Redis GET failed for {key}: {e}")
        return None

def safe_cache_set(key, val, ttl):
    try:
        cache.set(key, val, ttl)
    except Exception as e:
        logger.warning(f"Redis SET failed for {key}: {e}")

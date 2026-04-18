
import redis
from django.conf import settings

# Redis connection for personal lists
# redis_client = redis.StrictRedis(
#     host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB_PERSONAL_LISTS, decode_responses=True
# )

# Redis connection for personal lists, using the REDIS_URL or REDIS_URL_PERSONAL_LISTS
redis_client = redis.from_url(
    settings.REDIS_URL_PERSONAL_LISTS,
    decode_responses=True
)

def clean_expired_sessions():
    """
    Periodically cleans expired session data from Redis.
    
    NOTE: Redis automatically expires keys based on their TTL (set via setex).
    This task is a safeguard cleanup. We don't actively scan/delete since:
    - Redis handles automatic TTL-based expiration efficiently
    - keys("*") is O(N) and blocks on large datasets
    - setex() already handles expiration with 86400s (24h) TTL
    
    This task simply reports stats; actual cleanup is Redis automatic.
    """
    # Redis automatically cleans expired keys; this is a monitoring task
    info = redis_client.info()
    expired_count = info.get("expired_keys", 0)
    
    return {
        "status": "success",
        "expired_keys_auto_cleaned": expired_count,
        "note": "Redis TTL automatically handles expiration. This task monitors, not actively deletes."
    }
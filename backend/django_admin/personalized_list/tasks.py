

from celery import shared_task
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

@shared_task
def clean_expired_sessions():
    """
    Periodically cleans expired session data from Redis.
    """
    # Fetch all session keys
    session_keys = redis_client.keys("*")

    # Check expiration time and remove expired ones
    for key in session_keys:
        if redis_client.ttl(key) == -2:  # -2 means the key no longer exists (expired)
            redis_client.delete(key)

    return f"Checked {len(session_keys)} sessions and removed expired ones."
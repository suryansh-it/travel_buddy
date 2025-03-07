import algoliasearch as algolia
import os
import redis


# Redis setup
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

ALGOLIA_APP_ID = os.getenv("ALGOLIA_APP_ID")
ALGOLIA_API_KEY = os.getenv("ALGOLIA_API_KEY")
ALGOLIA_INDEX_NAME = "travel_apps"

client = algolia.SearchClient.create(ALGOLIA_APP_ID, ALGOLIA_API_KEY)
index = client.init_index(ALGOLIA_INDEX_NAME)

def search_apps(query):
    cache_key = f"search:{query}"
    cached_result = redis_client.get(cache_key)
    
    if cached_result:
        return eval(cached_result)
    
    results = index.search(query).get("hits", [])
    redis_client.setex(cache_key, 300, str(results))  # Cache for 5 minutes
    return results
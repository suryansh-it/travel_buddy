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

def search_countries(query):
    results = index.search(query)  # Perform Algolia search
    
    return [
        {
            "name": hit["name"],
            "code": hit["code"],
            "flag": hit.get("flag")
        }
        for hit in results.get("hits", [])
    ]
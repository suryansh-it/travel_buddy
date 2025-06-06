from google_play_scraper import search as gp_search

def search_play_store(keyword, country="in", limit=10):
    results = gp_search(keyword, lang="en", country=country, n_hits=limit)
    
    apps = []
    for app in results:
        apps.append({
            "name": app["title"],
            "app_id": app["appId"],
            "developer": app["developer"],  
            "rating": app.get("score", "N/A"),
            "reviews": app.get("reviews", "N/A"),
            "installs": app.get("installs", "N/A"),
            "url": f"https://play.google.com/store/apps/details?id={app['appId']}"
        })
    
    return apps

# Example usage
keyword = "payment"
country = "in"
play_store_apps = search_play_store(keyword, country)

print("\n📱 **Top 10 Apps from Google Play Store:**")
for i, app in enumerate(play_store_apps, 1):
    print(f"{i}. {app['name']} - {app['rating']}⭐ ({app['installs']} installs)")
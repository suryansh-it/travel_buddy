import requests

def search_app_store(keyword, country="us", limit=10):
    url = f"https://itunes.apple.com/search?term={keyword}&country={country}&entity=software&limit={limit}"
    response = requests.get(url)
    
    if response.status_code != 200:
        print("❌ Failed to fetch App Store data")
        return []
    
    data = response.json().get("results", [])
    apps = []

    for app in data:
        apps.append({
            "name": app.get("trackName", "N/A"),
            "app_id": app.get("trackId", "N/A"),
            "developer": app.get("artistName", "N/A"),
            "rating": app.get("averageUserRating", "N/A"),
            "reviews": app.get("userRatingCount", "N/A"),
            "price": app.get("price", "N/A"),
            "url": app.get("trackViewUrl", "N/A")
        })
    
    return apps

# Example usage
keyword = "payment"
country = "us"
app_store_apps = search_app_store(keyword, country)

print("\n🍏 **Top 10 Apps from Apple App Store:**")
for i, app in enumerate(app_store_apps, 1):
    print(f"{i}. {app['name']} - {app['rating']}⭐ ({app['reviews']} reviews, Price: {app['price']})")
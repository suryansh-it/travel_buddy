import psycopg2
import uuid

# Database connection parameters
conn = psycopg2.connect(
    dbname="travel_buddy_db",
    user="travel_buddy",  # Replace with your PostgreSQL username
    password="anujjainbatu",  # Replace with your PostgreSQL password
    host="localhost"
)

cur = conn.cursor()

# Insert country
cur.execute("""
    INSERT INTO countries (name, code) VALUES (%s, %s) RETURNING id;
""", ("China", "CN"))
country_id = cur.fetchone()[0]

# Insert categories
categories = [
    "Navigation & Maps",
    "Communication & Translation",
    "Currency Conversion & Finance",
    "Transportation & Ride-Hailing",
    "Booking & Accommodation",
    "Local Discovery & Reviews",
    "Emergency & Health",
    "Entertainment & Offline Content",
    "Internet & Connectivity",
    "Travel Planning & Itinerary Management"
]

category_ids = {}
for category in categories:
    cur.execute("""
        INSERT INTO categories (name) VALUES (%s) RETURNING id;
    """, (category,))
    category_ids[category] = cur.fetchone()[0]

# Insert apps
apps = [
    ("Amap (Gaode Maps)", "Best for local navigation but in Chinese.", category_ids["Navigation & Maps"]),
    ("Baidu Maps", "Another alternative for maps but also mostly in Chinese.", category_ids["Navigation & Maps"]),
    ("Apple Maps", "Works well for iPhone users in China.", category_ids["Navigation & Maps"]),
    ("Metro大都会", "Official app for Shanghai Metro, provides a QR code for scanning at stations.", category_ids["Navigation & Maps"]),
    ("WeChat", "Most common for messaging; often required for hotel communication.", category_ids["Communication & Translation"]),
    ("Baidu Translate", "Preferred over Google Translate for English-Chinese translations.", category_ids["Communication & Translation"]),
    ("Pleco", "The best offline Chinese dictionary.", category_ids["Communication & Translation"]),
    ("EZ Screen Translator", "Useful for scanning and translating text.", category_ids["Communication & Translation"]),
    ("Papago", "A translation app that works without a VPN.", category_ids["Communication & Translation"]),
    ("Alipay", "Preferred for foreigner-friendly mobile payments.", category_ids["Currency Conversion & Finance"]),
    ("WeChat Pay", "Alternative for payments but harder for foreigners to register.", category_ids["Currency Conversion & Finance"]),
    ("DiDi", "Standard ride-hailing app in China.", category_ids["Transportation & Ride-Hailing"]),
    ("Amap", "Can be used to book taxis, often cheaper than DiDi.", category_ids["Transportation & Ride-Hailing"]),
    ("Trip.com (CTrip)", "Main platform for booking flights, hotels, and train tickets.", category_ids["Booking & Accommodation"]),
    ("Qunar & Feizhu", "Alternative hotel booking apps, sometimes offering better deals.", category_ids["Booking & Accommodation"]),
    ("Meituan Dianping", "Equivalent to Yelp, provides restaurant reviews and food delivery.", category_ids["Local Discovery & Reviews"]),
    ("Museumfy", "For museum lovers, provides details about artworks.", category_ids["Local Discovery & Reviews"]),
    ("China Train Booking & 12306", "Essential for booking train tickets.", category_ids["Travel Planning & Itinerary Management"]),
    ("Trip.com", "All-in-one platform for travel planning.", category_ids["Travel Planning & Itinerary Management"])
]

for app in apps:
    cur.execute("""
        INSERT INTO apps (name, description, category_id) VALUES (%s, %s, %s) RETURNING id;
    """, (app[0], app[1], app[2]))
    app_id = cur.fetchone()[0]
    cur.execute("""
        INSERT INTO country_app_mapping (country_id, app_id) VALUES (%s, %s);
    """, (country_id, app_id))

# Commit the changes and close the connection
conn.commit()
cur.close()
conn.close()

print("Data inserted successfully.")
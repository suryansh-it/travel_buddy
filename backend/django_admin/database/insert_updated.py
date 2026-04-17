import uuid
from django.db import transaction
import sys,os
import django

# Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_admin.settings")  # Adjust if your settings file is elsewhere


# Set up Django environment
sys.path.append(r"D:\Dev\\python\\projects\\travel_buddy\backend\django_admin")  # Adjust path if needed
django.setup()

# Now import models
from country.models import Country, AppCategory, TravelApp  # Adjust import based on your Django app structure

# Clear existing data (if needed)
Country.objects.all().delete()
AppCategory.objects.all().delete()
TravelApp.objects.all().delete()

# Create Country
china, created = Country.objects.get_or_create(name="China", code="CN", description="Travel apps for China.")

# Create App Categories
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

category_map = {}
for category in categories:
    cat, _ = AppCategory.objects.get_or_create(name=category)
    category_map[category] = cat

# Travel Apps Data
apps = [
    ("Amap (Gaode Maps)", "Best for local navigation but in Chinese.", "Navigation & Maps"),
    ("Baidu Maps", "Another alternative for maps but also mostly in Chinese.", "Navigation & Maps"),
    ("Apple Maps", "Works well for iPhone users in China.", "Navigation & Maps"),
    ("Metro大都会", "Official app for Shanghai Metro, provides a QR code for scanning at stations.", "Navigation & Maps"),
    ("WeChat", "Most common for messaging; often required for hotel communication.", "Communication & Translation"),
    ("Baidu Translate", "Preferred over Google Translate for English-Chinese translations.", "Communication & Translation"),
    ("Pleco", "The best offline Chinese dictionary.", "Communication & Translation"),
    ("EZ Screen Translator", "Useful for scanning and translating text.", "Communication & Translation"),
    ("Papago", "A translation app that works without a VPN.", "Communication & Translation"),
    ("Alipay", "Preferred for foreigner-friendly mobile payments.", "Currency Conversion & Finance"),
    ("WeChat Pay", "Alternative for payments but harder for foreigners to register.", "Currency Conversion & Finance"),
    ("DiDi", "Standard ride-hailing app in China.", "Transportation & Ride-Hailing"),
    ("Amap", "Can be used to book taxis, often cheaper than DiDi.", "Transportation & Ride-Hailing"),
    ("Trip.com (CTrip)", "Main platform for booking flights, hotels, and train tickets.", "Booking & Accommodation"),
    ("Qunar & Feizhu", "Alternative hotel booking apps, sometimes offering better deals.", "Booking & Accommodation"),
    ("Meituan Dianping", "Equivalent to Yelp, provides restaurant reviews and food delivery.", "Local Discovery & Reviews"),
    ("Museumfy", "For museum lovers, provides details about artworks.", "Local Discovery & Reviews"),
    ("China Train Booking & 12306", "Essential for booking train tickets.", "Travel Planning & Itinerary Management"),
    ("Trip.com", "All-in-one platform for travel planning.", "Travel Planning & Itinerary Management")
]

# Insert Apps
with transaction.atomic():
    for name, description, category_name in apps:
        TravelApp.objects.create(
            name=name,
            description=description,
            category=category_map[category_name],
            country=china,
            icon_url="https://via.placeholder.com/100",  # Placeholder, update later
            android_link="https://play.google.com/store/apps/details?id=example",
            ios_link="https://apps.apple.com/app/example",
            website_link="https://example.com",
            supports_foreign_cards=False,
            works_offline=False
        )

print("✅ Data inserted successfully!")

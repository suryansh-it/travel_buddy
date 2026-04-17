# country/management/commands/import_from_excel.py

import os
import re
import time
import pandas as pd
import requests

from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

from google_play_scraper import app as gp_app

from country.models import Country, AppCategory, TravelApp

# Path to your uploaded Excel file. Adjust as needed.
EXCEL_PATH = os.path.join(settings.BASE_DIR, "country/management/commands/TRIPBOZO.xlsx")

PLAY_COUNTRY = "us"
APP_COUNTRY = "us"


def extract_play_app_id(play_url: str) -> str:
    match = re.search(r"[?&]id=([\w\.]+)", str(play_url))
    return match.group(1) if match else ""


def extract_ios_track_id(ios_url: str) -> str:
    match = re.search(r"/id(\d+)", str(ios_url))
    return match.group(1) if match else ""


def scrape_play_details_by_url(play_url: str) -> dict:
    app_id = extract_play_app_id(play_url)
    if not app_id:
        return {}
    try:
        details = gp_app(app_id, lang="en", country=PLAY_COUNTRY)
        return {
            "android_link": f"https://play.google.com/store/apps/details?id={app_id}",
            "play_rating": details.get("score"),
            "play_installs": details.get("installs"),
            "description_play": details.get("description"),
            "icon": details.get("icon"),
        }
    except Exception:
        return {}


def scrape_app_store_by_url(ios_url: str) -> dict:
    track_id = extract_ios_track_id(ios_url)
    if not track_id:
        return {}
    try:
        lookup_url = f"https://itunes.apple.com/lookup?id={track_id}&country={APP_COUNTRY}"
        r = requests.get(lookup_url, timeout=10)
        if r.status_code != 200:
            return {}
        results = r.json().get("results", [])
        if not results:
            return {}
        top = results[0]
        return {
            "ios_link": top.get("trackViewUrl"),
            "ios_rating": top.get("averageUserRating"),
            "description_ios": top.get("description"),
            "icon_ios": top.get("artworkUrl100"),
        }
    except Exception:
        return {}


def scrape_play_store_by_name(name: str, country=PLAY_COUNTRY, limit=1) -> dict:
    try:
        from google_play_scraper import search as gp_search
        hits = gp_search(name, lang="en", country=country, n_hits=limit)
        if not hits:
            return {}
        top = hits[0]
        return {
            "android_link": f"https://play.google.com/store/apps/details?id={top['appId']}",
            "play_rating": top.get("score"),
            "play_installs": top.get("installs"),
            "description_play": top.get("description"),
            "icon": top.get("icon"),
        }
    except Exception:
        return {}


def scrape_app_store_by_name(name: str, country=APP_COUNTRY, limit=1) -> dict:
    try:
        from requests.utils import quote
        term = quote(name)
        url = f"https://itunes.apple.com/search?term={term}&country={country}&entity=software&limit={limit}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return {}
        data = r.json().get("results", [])
        if not data:
            return {}
        top = data[0]
        return {
            "ios_link": top.get("trackViewUrl"),
            "ios_rating": top.get("averageUserRating"),
            "description_ios": top.get("description"),
            "icon_ios": top.get("artworkUrl100"),
        }
    except Exception:
        return {}


class Command(BaseCommand):
    help = "Import Country, AppCategory, TravelApp from Excel and enrich via scrapers"

    def handle(self, *args, **options):
        # 1) Verify the Excel file exists
        if not os.path.exists(EXCEL_PATH):
            self.stderr.write(f"❌ Excel file not found at {EXCEL_PATH}")
            return

        # 2) Load spreadsheet
        try:
            df = pd.read_excel(EXCEL_PATH)
        except Exception as e:
            self.stderr.write(f"❌ Failed to read Excel: {e}")
            return

        # 3) Normalize column names
        df.columns = [col.strip() for col in df.columns]

        # 3a) If user typed “Catrgory” instead of “Category”, rename it
        if "Catrgory" in df.columns:
            df.rename(columns={"Catrgory": "Category"}, inplace=True)

        # 3b) Required columns
        required = {"Country", "Code", "Category", "App Name"}
        if not required.issubset(df.columns):
            self.stderr.write(
                "❌ Excel must contain these columns: Country, Code, Category, App Name"
            )
            self.stderr.write(f"    → Found columns: {list(df.columns)}")
            return

        # 4) Detect optional columns
        has_android_col = "Android Link" in df.columns
        has_ios_col     = "iOS Link" in df.columns
        has_website_col = "Website Link" in df.columns
        has_desc_col    = "Description" in df.columns

        rows = df.to_dict(orient="records")
        total = len(rows)
        self.stdout.write(f"🔄 Processing {total} rows…")

        with transaction.atomic():
            for idx, row in enumerate(rows, start=1):
                country_name = str(row["Country"]).strip()
                country_code = str(row["Code"]).strip().upper()
                category_name = str(row["Category"]).strip()
                app_name = str(row["App Name"]).strip()

                sheet_android = str(row["Android Link"]).strip() if has_android_col else None
                sheet_ios     = str(row["iOS Link"]).strip() if has_ios_col else None
                sheet_web     = str(row["Website Link"]).strip() if has_website_col else None
                sheet_desc    = str(row["Description"]).strip() if has_desc_col else None

                # 5a) Country
                country_obj, _ = Country.objects.get_or_create(
                    code=country_code,
                    defaults={"name": country_name}
                )

                # 5b) Category
                category_obj, _ = AppCategory.objects.get_or_create(name=category_name)

                # 5c) TravelApp: look up by (country, name) because of unique_together
                try:
                    app_obj = TravelApp.objects.get(country=country_obj, name=app_name)
                    created = False
                except TravelApp.DoesNotExist:
                    app_obj = TravelApp.objects.create(
                        name=app_name,
                        country=country_obj,
                        category=category_obj,
                        description=(sheet_desc or "")
                    )
                    created = True
                    self.stdout.write(f"[{idx}/{total}] ➕ Created TravelApp: {app_name}")

                changed = False

                # 6) If sheet provided an Android Link, store it
                if sheet_android:
                    if app_obj.android_link != sheet_android:
                        app_obj.android_link = sheet_android
                        changed = True

                # 7) If sheet provided an iOS Link, store it
                if sheet_ios:
                    if app_obj.ios_link != sheet_ios:
                        app_obj.ios_link = sheet_ios
                        changed = True

                # 8) If sheet provided a Website Link, store it
                if sheet_web:
                    if app_obj.website_link != sheet_web:
                        app_obj.website_link = sheet_web
                        changed = True

                # 9) If sheet provided a Description, store it if missing
                if sheet_desc and not app_obj.description:
                    app_obj.description = sheet_desc
                    changed = True

                # 10) Enrich via scrapers
                # PLAY STORE:
                if not app_obj.android_link:
                    data_play = scrape_play_store_by_name(app_name)
                else:
                    data_play = scrape_play_details_by_url(app_obj.android_link)

                if data_play.get("android_link") and not app_obj.android_link:
                    app_obj.android_link = data_play["android_link"]
                    changed = True

                if data_play.get("description_play") and not app_obj.description:
                    app_obj.description = data_play["description_play"].strip()
                    changed = True

                if data_play.get("icon") and not app_obj.icon_url:
                    app_obj.icon_url = data_play["icon"]
                    changed = True

                # IOS STORE:
                if not app_obj.ios_link:
                    data_ios = scrape_app_store_by_name(app_name)
                else:
                    data_ios = scrape_app_store_by_url(app_obj.ios_link)

                if data_ios.get("ios_link") and not app_obj.ios_link:
                    app_obj.ios_link = data_ios["ios_link"]
                    changed = True

                if data_ios.get("description_ios") and not app_obj.description:
                    app_obj.description = data_ios["description_ios"].strip()
                    changed = True

                if data_ios.get("icon_ios") and not app_obj.icon_url:
                    app_obj.icon_url = data_ios["icon_ios"]
                    changed = True

                # 11) Save if changed
                if changed:
                    app_obj.save()
                    self.stdout.write(f"    ↪ Enriched: {app_name}")

                # throttle so we don’t hit rate limits
                time.sleep(0.5)

        self.stdout.write(self.style.SUCCESS("✅ Import & enrichment complete"))


# import os
# import time
# import pandas as pd
# import requests

# from django.core.management.base import BaseCommand
# from django.db import transaction
# from django.conf import settings

# from google_play_scraper import search as gp_search

# from country.models import Country, AppCategory, TravelApp

# EXCEL_PATH = os.path.join(settings.BASE_DIR, "country\management\commands\Travel_Buddy.xlsx")
# # Adjust above if your BASE_DIR differs

# PLAY_COUNTRY = "us"
# APP_COUNTRY  = "us"
# PLAY_LIMIT   = 1
# APP_LIMIT    = 1

# def scrape_play_store(name, country=PLAY_COUNTRY, limit=PLAY_LIMIT):
#     """Return dict with android_link, play_rating, play_installs, description_play."""
#     try:
#         hits = gp_search(name, lang="en", country=country, n_hits=limit)
#         if not hits: return {}
#         top = hits[0]
#         return {
#             "android_link": f"https://play.google.com/store/apps/details?id={top['appId']}",
#             "play_rating": top.get("score"),
#             "play_installs": top.get("installs"),
#             "description_play": top.get("description"),
#         }
#     except Exception:
#         return {}

# def scrape_app_store(name, country=APP_COUNTRY, limit=APP_LIMIT):
#     """Return dict with ios_link, ios_rating, description_ios."""
#     try:
#         term = requests.utils.quote(name)
#         url = (
#             f"https://itunes.apple.com/search"
#             f"?term={term}&country={country}&entity=software&limit={limit}"
#         )
#         r = requests.get(url, timeout=10)
#         if r.status_code != 200: return {}
#         results = r.json().get("results", [])
#         if not results: return {}
#         top = results[0]
#         return {
#             "ios_link": top.get("trackViewUrl"),
#             "ios_rating": top.get("averageUserRating"),
#             "description_ios": top.get("description"),
#         }
#     except Exception:
#         return {}

# class Command(BaseCommand):
#     help = "Import Country, AppCategory, TravelApp from Excel and enrich via scrapers"

#     def handle(self, *args, **options):
#         if not os.path.exists(EXCEL_PATH):
#             self.stderr.write(f"❌ Excel file not found at {EXCEL_PATH}")
#             return

#         # 1) Load spreadsheet
#         try:
#             df = pd.read_excel(EXCEL_PATH)
#         except Exception as e:
#             self.stderr.write(f"❌ Failed to read Excel: {e}")
#             return

#         # 2) Normalize column names
#         df.columns = [col.strip() for col in df.columns]
#         required = {"Country", "Code", "Category", "App Name"}
#         if not required.issubset(df.columns):
#             self.stderr.write(
#                 "❌ Excel must contain columns: Country, Code, Category, App Name"
#             )
#             return

#         rows = df.to_dict(orient="records")
#         self.stdout.write(f"🔄 Processing {len(rows)} rows…")

#         with transaction.atomic():
#             for idx, row in enumerate(rows, 1):
#                 cname = row["Country"]
#                 ccode = str(row["Code"]).strip().upper()
#                 cat   = row["Category"]
#                 aname = row["App Name"]
#                 desc0 = row.get("Description") or ""

#                 # 3a) Country
#                 country, _ = Country.objects.get_or_create(
#                     code=ccode,
#                     defaults={"name": cname}
#                 )

#                 # 3b) Category
#                 category, _ = AppCategory.objects.get_or_create(name=cat)

#                 # 3c) TravelApp
#                 app, created = TravelApp.objects.get_or_create(
#                     name=aname,
#                     country=country,
#                     category=category,
#                     defaults={"description": desc0}
#                 )
#                 if created:
#                     self.stdout.write(f"[{idx}] ➕ Created app: {aname}")

#                 # 4) Enrich via scrapers if missing
#                 changed = False

#                 # Play Store
#                 if not app.android_link:
#                     data = scrape_play_store(aname)
#                     if data.get("android_link"):
#                         app.android_link = data["android_link"]
#                         app.description  = app.description or data.get("description_play")
#                         changed = True

#                 # App Store
#                 if not app.ios_link:
#                     data2 = scrape_app_store(aname)
#                     if data2.get("ios_link"):
#                         app.ios_link     = data2["ios_link"]
#                         app.description  = app.description or data2.get("description_ios")
#                         changed = True

#                 if changed:
#                     app.save()
#                     self.stdout.write(f"    ↪ Enriched: {aname}")

#                 # throttle a bit
#                 time.sleep(0.5)

#         self.stdout.write(self.style.SUCCESS("✅ Import & enrichment complete"))

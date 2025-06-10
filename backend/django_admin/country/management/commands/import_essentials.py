import os
import pandas as pd
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.shortcuts import get_object_or_404

# Assuming these models are correctly defined in country.models
from country.models import Country, EmergencyContact, LocalPhrase, UsefulTip


# Convert these paths to Path objects
# In a real Django environment, settings.BASE_DIR would point to your project's base directory.
# Ensure these CSV files are located at:
# <your_project_root>/backend/django_admin/country/management/commands/
EMERGENCY_CSV = Path(os.path.join(settings.BASE_DIR, "country/management/commands/emergency_contacts.csv"))
PHRASES_CSV = Path(os.path.join(settings.BASE_DIR, "country/management/commands/local_phrases.csv"))
TIPS_CSV = Path(os.path.join(settings.BASE_DIR, "country/management/commands/useful_tips.csv"))

class Command(BaseCommand):
    help = "Import emergency contacts, local phrases and useful tips from CSVs"

    def handle(self, *args, **options):
        # 1) check for presence of all three files
        missing = [p for p in (EMERGENCY_CSV, PHRASES_CSV, TIPS_CSV) if not p.exists()]
        if missing:
            for p in missing:
                self.stderr.write(f"❌ CSV not found: {p}")
            return

        # 2) read them
        try:
            # When reading with pandas, you can pass Path objects directly
            self.stdout.write("Reading CSV files...")
            df_em = pd.read_csv(EMERGENCY_CSV)
            df_ph = pd.read_csv(PHRASES_CSV)
            df_tips = pd.read_csv(TIPS_CSV)
            self.stdout.write("✅ CSV files read successfully.")
        except Exception as e:
            self.stderr.write(f"❌ Failed reading CSVs: {e}")
            return

        with transaction.atomic():
            self.stdout.write("Starting data import within a transaction...")

            # Emergencies
            self.stdout.write("\nImporting Emergency Contacts...")
            for _, row in df_em.iterrows():
                # Corrected: Use 'country_code' as per the CSV header observed in previous turns
                code = str(row.get("country_code", "")).strip().upper()
                name = str(row.get("name", "")).strip()
                phone = str(row.get("phone", "")).strip()
                email = str(row.get("email", "")).strip() or None
                desc = str(row.get("description", "")).strip() or None

                if not (code and name and phone):
                    self.stderr.write(f"⚠️ Skipping EmergencyContact row: Missing 'country_code', 'name', or 'phone'. Data: {row.to_dict()}")
                    continue

                try:
                    country = get_object_or_404(Country, code=code)
                    obj, created = EmergencyContact.objects.update_or_create(
                        country=country, name=name,
                        defaults={"phone": phone, "email": email, "description": desc}
                    )
                    verb = "Created" if created else "Updated"
                    self.stdout.write(f"[Emergency] {verb} {country.code} → {name}")
                except Exception as e:
                    self.stderr.write(f"❌ Error importing EmergencyContact for {name} ({code}): {e}")
                    # Optionally, re-raise or handle more gracefully if you want to stop on error
                    continue


            # Phrases
            self.stdout.write("\nImporting Local Phrases...")
            for _, row in df_ph.iterrows():
                # Corrected: Use 'country_code' as per the CSV header observed in previous turns
                code = str(row.get("country_code", "")).strip().upper()
                orig = str(row.get("original", "")).strip()
                trans = str(row.get("translation", "")).strip() or ""
                note = str(row.get("context_note", "")).strip() or None

                if not (code and orig):
                    self.stderr.write(f"⚠️ Skipping LocalPhrase row: Missing 'country_code' or 'original'. Data: {row.to_dict()}")
                    continue

                try:
                    country = get_object_or_404(Country, code=code)
                    obj, created = LocalPhrase.objects.update_or_create(
                        country=country, original=orig,
                        defaults={"translation": trans, "context_note": note}
                    )
                    verb = "Created" if created else "Updated"
                    self.stdout.write(f"[Phrase] {verb} {country.code} → “{orig}”")
                except Exception as e:
                    self.stderr.write(f"❌ Error importing LocalPhrase for “{orig}” ({code}): {e}")
                    continue


            # Tips
            self.stdout.write("\nImporting Useful Tips...")
            for _, row in df_tips.iterrows():
                # Corrected: Use 'country_code' as per the CSV header observed in previous turns
                code = str(row.get("country_code", "")).strip().upper()
                tip_txt = str(row.get("tip", "")).strip()

                if not (code and tip_txt):
                    self.stderr.write(f"⚠️ Skipping UsefulTip row: Missing 'country_code' or 'tip'. Data: {row.to_dict()}")
                    continue

                try:
                    country = get_object_or_404(Country, code=code)
                    obj, created = UsefulTip.objects.get_or_create(
                        country=country, tip=tip_txt
                    )
                    if created:
                        self.stdout.write(f"[Tip] Created {country.code} → {tip_txt[:50]}...") # Log first 50 chars of tip
                    else:
                        self.stdout.write(f"[Tip] Existing {country.code} → {tip_txt[:50]}...") # Log existing tips too
                except Exception as e:
                    self.stderr.write(f"❌ Error importing UsefulTip for {tip_txt[:30]}... ({code}): {e}")
                    continue

        self.stdout.write(self.style.SUCCESS("✅ Essentials import complete"))
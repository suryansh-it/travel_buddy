# country/management/commands/import_essentials.py

import os
import pandas as pd

from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from django.shortcuts import get_object_or_404

from country.models import Country, EmergencyContact, LocalPhrase, UsefulTip

EXCEL_PATH = os.path.join(settings.BASE_DIR, "country/management/commands/country_essentials_dataset.xlsx")

# Expected sheet names:
EMERGENCY_SHEET = "Emergencies"
PHRASES_SHEET   = "Phrases"
TIPS_SHEET      = "Tips"

class Command(BaseCommand):
    help = "Import emergency contacts, local phrases and useful tips from Excel"

    def handle(self, *args, **options):
        if not os.path.exists(EXCEL_PATH):
            self.stderr.write(f"❌ Excel file not found at {EXCEL_PATH}")
            return

        # Read all sheets at once
        try:
            xls = pd.read_excel(EXCEL_PATH, sheet_name=[EMERGENCY_SHEET, PHRASES_SHEET, TIPS_SHEET])
        except Exception as e:
            self.stderr.write(f"❌ Failed to read Excel: {e}")
            return

        with transaction.atomic():
            # 1) Emergencies
            df_em = xls.get(EMERGENCY_SHEET, pd.DataFrame())
            for idx, row in df_em.iterrows():
                code = str(row.get("Code", "")).strip().upper()
                name = str(row.get("Name", "")).strip()
                phone = str(row.get("Phone", "")).strip()
                email = str(row.get("Email", "")).strip() or None
                desc = str(row.get("Description", "")).strip() or None

                if not code or not name or not phone:
                    continue  # skip incomplete

                country = get_object_or_404(Country, code=code)
                obj, created = EmergencyContact.objects.update_or_create(
                    country=country, name=name,
                    defaults={"phone": phone, "email": email, "description": desc}
                )
                action = "Created" if created else "Updated"
                self.stdout.write(f"[Emergency] {action} {country.code} → {name}")

            # 2) Phrases
            df_ph = xls.get(PHRASES_SHEET, pd.DataFrame())
            for idx, row in df_ph.iterrows():
                code = str(row.get("Code", "")).strip().upper()
                orig = str(row.get("Original", "")).strip()
                trans = str(row.get("Translation", "")).strip() or ""
                note  = str(row.get("Context Note", "")).strip() or None

                if not code or not orig:
                    continue

                country = get_object_or_404(Country, code=code)
                obj, created = LocalPhrase.objects.update_or_create(
                    country=country, original=orig,
                    defaults={"translation": trans, "context_note": note}
                )
                action = "Created" if created else "Updated"
                self.stdout.write(f"[Phrase] {action} {country.code} → “{orig}”")

            # 3) Tips
            df_tips = xls.get(TIPS_SHEET, pd.DataFrame())
            for idx, row in df_tips.iterrows():
                code = str(row.get("Code", "")).strip().upper()
                tip_text = str(row.get("Tip", "")).strip()

                if not code or not tip_text:
                    continue

                country = get_object_or_404(Country, code=code)
                obj, created = UsefulTip.objects.get_or_create(
                    country=country, tip=tip_text
                )
                if created:
                    self.stdout.write(f"[Tip] Created {country.code} → {tip_text[:30]}…")

        self.stdout.write(self.style.SUCCESS("✅ Essentials import complete"))

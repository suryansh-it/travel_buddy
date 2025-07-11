# country/management/commands/import_countries.py

import os
from pathlib import Path
import pandas as pd

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from country.models import Country


class Command(BaseCommand):
    help = "Import countries from CSV or XLSX into the Country model."

    def handle(self, *args, **options):
        from openpyxl import load_workbook

        # Define the path to countries.xlsx
        EXCEL_PATH = os.path.join(settings.BASE_DIR, "country/management/commands/countries.xlsx")

        self.stdout.write(f"📄 Looking for: {EXCEL_PATH}")

        if not os.path.exists(EXCEL_PATH):
            self.stderr.write(f"❌ File not found: {EXCEL_PATH}")
            return

        try:
            self.stdout.write("🔄 Reading Excel file...")
            df_countries = pd.read_excel(EXCEL_PATH)
            self.stdout.write(f"✅ Loaded {len(df_countries)} rows from countries.xlsx")
        except Exception as e:
            self.stderr.write(f"❌ Failed to read Excel file: {e}")
            return

        total_created, total_updated, total_skipped = 0, 0, 0

        with transaction.atomic():
            for idx, row in df_countries.iterrows():
                name = str(row.get("name", "")).strip()
                code = str(row.get("code", "")).strip().upper()
                description = str(row.get("description", "")).strip() if row.get("description") else ""

                if not name or not code:
                    self.stderr.write(f"⚠️ Skipping row {idx + 2}: Missing name/code")
                    total_skipped += 1
                    continue

                try:
                    obj, created = Country.objects.update_or_create(
                        name=name,
                        defaults={"code": code, "description": description}
                    )
                    if created:
                        self.stdout.write(f"  ➕ Created: {name} ({code}) {description}")
                        total_created += 1
                    else:
                        self.stdout.write(f"  🔄 Updated: {name} ({code}) {description}")
                        total_updated += 1
                except Exception as e:
                    self.stderr.write(f"❌ Error in row {idx + 2}: {e}")
                    total_skipped += 1

        self.stdout.write(self.style.SUCCESS(f"\n✅ Done! {total_created} created, {total_updated} updated, {total_skipped} skipped."))

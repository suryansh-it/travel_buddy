import os
import pandas as pd
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

# Import your Country model
from country.models import Country

class Command(BaseCommand):
    help = "Import countries from countries.csv into the Country model."

    def handle(self, *args, **options):
        # Define the path to the countries.csv file.
        # It's assumed to be in the same directory as this management command.
        # Adjust the path if your countries.csv is located elsewhere.
        countries_csv_path = Path(os.path.join(
            settings.BASE_DIR,
            "country/management/commands/countries.csv" # Adjust this path if necessary
        ))

        self.stdout.write(f"Attempting to import countries from: {countries_csv_path}")

        # 1. Check for the presence of the CSV file
        if not countries_csv_path.exists():
            self.stderr.write(f"❌ Error: CSV file not found at {countries_csv_path}")
            self.stderr.write("Please ensure 'countries.csv' is in the specified path.")
            return

        # 2. Read the CSV file using pandas
        try:
            self.stdout.write("Reading countries.csv...")
            df_countries = pd.read_csv(countries_csv_path)
            self.stdout.write(f"✅ Successfully read {len(df_countries)} rows from countries.csv.")
            # self.stdout.write("\nFirst 5 rows of the CSV:")
            # self.stdout.write(df_countries.head().to_string()) # Uncomment for debugging CSV content
        except Exception as e:
            self.stderr.write(f"❌ Failed to read countries.csv: {e}")
            return

        # 3. Import data into the Country model within a database transaction
        total_created = 0
        total_updated = 0
        total_skipped = 0

        with transaction.atomic():
            self.stdout.write("\nStarting database import for Countries...")
            for index, row in df_countries.iterrows():
                # Extract data from the row.
                # .get() is used for safety, providing an empty string fallback.
                name = str(row.get("name", "")).strip()
                code = str(row.get("code", "")).strip().upper() # Ensure code is uppercase for consistency
                # Description is optional based on your Country model
                description = str(row.get("description", "")).strip() if row.get("description") else None

                # Validate essential fields
                if not name:
                    self.stderr.write(f"⚠️ Skipping row {index + 1}: 'name' is missing. Row data: {row.to_dict()}")
                    total_skipped += 1
                    continue
                if not code:
                    self.stderr.write(f"⚠️ Skipping row {index + 1}: 'code' is missing. Row data: {row.to_dict()}")
                    total_skipped += 1
                    continue

                try:
                    # Use update_or_create to add new countries or update existing ones.
                    # It matches on 'code' and updates 'name' and 'description'.
                    country_obj, created = Country.objects.update_or_create(
                        code=code,
                        defaults={"name": name, "description": description}
                    )

                    if created:
                        self.stdout.write(f"  ➕ Created Country: {name} (Code: {code})")
                        total_created += 1
                    else:
                        self.stdout.write(f"  🔄 Updated Country: {name} (Code: {code})")
                        total_updated += 1

                except Exception as e:
                    self.stderr.write(f"❌ Error processing row {index + 1} for country {name} ({code}): {e}")
                    total_skipped += 1
                    # Continue to the next row even if one fails, but log the error
                    continue

        self.stdout.write(self.style.SUCCESS("\n✅ Country import process complete!"))
        self.stdout.write(self.style.SUCCESS(f"Summary: {total_created} created, {total_updated} updated, {total_skipped} skipped."))
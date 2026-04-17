import os
import pandas as pd
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.shortcuts import get_object_or_404

from country.models import Country, EmergencyContact, LocalPhrase, UsefulTip

EMERGENCY_CSV = Path(settings.BASE_DIR) / "country/management/commands/emergency_contacts.csv"
PHRASES_CSV   = Path(settings.BASE_DIR) / "country/management/commands/local_phrases.csv"
TIPS_CSV      = Path(settings.BASE_DIR) / "country/management/commands/useful_tips.csv"

class Command(BaseCommand):
    help = "Import emergency contacts, local phrases and useful tips from CSVs, only new or changed rows"

    def handle(self, *args, **options):
        missing = [p for p in (EMERGENCY_CSV, PHRASES_CSV, TIPS_CSV) if not p.exists()]
        if missing:
            for p in missing:
                self.stderr.write(f"❌ CSV not found: {p}")
            return

        try:
            self.stdout.write("📥 Reading CSV files…")
            df_em   = pd.read_csv(EMERGENCY_CSV)
            df_ph   = pd.read_csv(PHRASES_CSV)
            df_tips = pd.read_csv(TIPS_CSV)
            self.stdout.write("✅ CSVs loaded")
        except Exception as e:
            self.stderr.write(f"❌ Failed to read CSVs: {e}")
            return

        with transaction.atomic():
            self.stdout.write("🛠️ Starting import…")

            # --- Emergency Contacts ---
            self.stdout.write("\n🔔 Emergency Contacts")
            for _, row in df_em.iterrows():
                code  = str(row.get("country_code","")).strip().upper()
                name  = str(row.get("name","")).strip()
                phone = str(row.get("phone","")).strip()
                email= str(row.get("email","")).strip() or None
                desc = str(row.get("description","")).strip() or None

                if not (code and name and phone):
                    self.stderr.write(f"⚠️ Skip EM row missing key fields: {row.to_dict()}")
                    continue

                country = get_object_or_404(Country, code=code)
                # try to fetch existing
                ec = EmergencyContact.objects.filter(country=country, name=name).first()
                if ec:
                    # compare fields
                    if ec.phone==phone and ec.email==email and ec.description==desc:
                        self.stdout.write(f"  ↳ Unchanged: {code} → {name}")
                        continue
                    # update only changed
                    ec.phone       = phone
                    ec.email       = email
                    ec.description = desc
                    ec.save()
                    self.stdout.write(f"  🔄 Updated:   {code} → {name}")
                else:
                    EmergencyContact.objects.create(
                        country=country, name=name,
                        phone=phone, email=email, description=desc
                    )
                    self.stdout.write(f"  ➕ Created:   {code} → {name}")

            # --- Local Phrases ---
            self.stdout.write("\n💬 Local Phrases")
            for _, row in df_ph.iterrows():
                code = str(row.get("country_code","")).strip().upper()
                orig  = str(row.get("original","")).strip()
                trans= str(row.get("translation","")).strip() or ""
                note = str(row.get("context_note","")).strip() or None

                if not (code and orig):
                    self.stderr.write(f"⚠️ Skip PH row missing key: {row.to_dict()}")
                    continue

                country = get_object_or_404(Country, code=code)
                lp = LocalPhrase.objects.filter(country=country, original=orig).first()
                if lp:
                    if lp.translation==trans and lp.context_note==note:
                        self.stdout.write(f"  ↳ Unchanged: {code} → “{orig}”")
                        continue
                    lp.translation  = trans
                    lp.context_note = note
                    lp.save()
                    self.stdout.write(f"  🔄 Updated:   {code} → “{orig}”")
                else:
                    LocalPhrase.objects.create(
                        country=country, original=orig,
                        translation=trans, context_note=note
                    )
                    self.stdout.write(f"  ➕ Created:   {code} → “{orig}”")

            # --- Useful Tips ---
            self.stdout.write("\n💡 Useful Tips")
            for _, row in df_tips.iterrows():
                code   = str(row.get("country_code","")).strip().upper()
                tip_txt= str(row.get("tip","")).strip()

                if not (code and tip_txt):
                    self.stderr.write(f"⚠️ Skip TIP row missing key: {row.to_dict()}")
                    continue

                country = get_object_or_404(Country, code=code)
                ut = UsefulTip.objects.filter(country=country, tip=tip_txt).first()
                if ut:
                    self.stdout.write(f"  ↳ Exists:    {code} → {tip_txt[:30]}…")
                else:
                    UsefulTip.objects.create(country=country, tip=tip_txt)
                    self.stdout.write(f"  ➕ Created:   {code} → {tip_txt[:30]}…")

        self.stdout.write(self.style.SUCCESS("✅ Import complete"))

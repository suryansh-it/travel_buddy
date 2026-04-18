from django.core.management.base import BaseCommand

from country.tasks import refresh_travel_updates_batch


class Command(BaseCommand):
    help = "Refresh travel updates cache for a rotating subset of countries."

    def handle(self, *args, **options):
        result = refresh_travel_updates_batch()
        self.stdout.write(self.style.SUCCESS(f"Travel updates refresh complete: {result}"))

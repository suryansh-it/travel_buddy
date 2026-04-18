from django.core.management.base import BaseCommand

from country.tasks import refresh_traveler_insights_batch


class Command(BaseCommand):
    help = "Refresh traveler insights cache for a rotating subset of apps."

    def handle(self, *args, **options):
        result = refresh_traveler_insights_batch()
        self.stdout.write(self.style.SUCCESS(f"Traveler insights refresh complete: {result}"))

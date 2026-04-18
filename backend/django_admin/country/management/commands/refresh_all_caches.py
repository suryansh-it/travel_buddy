from django.core.management.base import BaseCommand
import logging

from country.tasks import refresh_travel_updates_batch, refresh_traveler_insights_batch
from personalized_list.tasks import clean_expired_sessions

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Refresh all caches and monitoring: travel updates, traveler insights, and session cleanup."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("[START] Full cache refresh..."))
        
        try:
            # Refresh travel updates
            result1 = refresh_travel_updates_batch()
            self.stdout.write(f"  [OK] Travel updates: {result1}")
        except Exception as e:
            logger.error(f"Travel updates failed: {e}")
            self.stdout.write(self.style.ERROR(f"  [ERROR] Travel updates: {e}"))
        
        try:
            # Refresh traveler insights
            result2 = refresh_traveler_insights_batch()
            self.stdout.write(f"  [OK] Traveler insights: {result2}")
        except Exception as e:
            logger.error(f"Traveler insights failed: {e}")
            self.stdout.write(self.style.ERROR(f"  [ERROR] Traveler insights: {e}"))
        
        try:
            # Clean expired sessions
            result3 = clean_expired_sessions()
            self.stdout.write(f"  [OK] Session cleanup: {result3}")
        except Exception as e:
            logger.error(f"Session cleanup failed: {e}")
            self.stdout.write(self.style.ERROR(f"  [ERROR] Session cleanup: {e}"))
        
        self.stdout.write(self.style.SUCCESS("[DONE] Full cache refresh complete!"))

from django.core.management.base import BaseCommand

from personalized_list.tasks import clean_expired_sessions


class Command(BaseCommand):
    help = "Check personal-list Redis key expiration stats."

    def handle(self, *args, **options):
        result = clean_expired_sessions()
        self.stdout.write(self.style.SUCCESS(f"Session cleanup monitor complete: {result}"))

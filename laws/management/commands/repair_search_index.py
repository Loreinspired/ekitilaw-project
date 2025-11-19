from django.core.management.base import BaseCommand
from laws.models import Law
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Regenerates slugs for all laws and re-syncs the Meilisearch index'

    def handle(self, *args, **kwargs):
        self.stdout.write("1. Checking Law Slugs...")
        
        laws = Law.objects.all()
        count = 0
        for law in laws:
            if not law.slug:
                # Saving triggers the slugify logic in your model
                law.save()
                count += 1
                self.stdout.write(f"   - Fixed slug for: {law.title}")
        
        self.stdout.write(f"   Success: {count} laws repaired.")
        
        self.stdout.write("2. Syncing Search Index (This may take time)...")
        
        try:
            self.stdout.write("   - Syncing Sections...")
            call_command('syncindex', 'laws.Section', verbosity=1)
            
            self.stdout.write("   - Syncing Schedules...")
            call_command('syncindex', 'laws.Schedule', verbosity=1)
            
            self.stdout.write("   - Syncing Appendices...")
            call_command('syncindex', 'laws.Appendix', verbosity=1)
            
            self.stdout.write(self.style.SUCCESS("DONE: Index is fully synchronized."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Index sync failed: {e}"))
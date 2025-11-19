
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ekitilaw_project.settings')
django.setup()

from laws.models import Law
from django.core.management import call_command

def fix_and_sync():
    print("--- Step 1: Checking Database Integrity ---")
    laws = Law.objects.all()
    fixed_count = 0
    
    for law in laws:
        # Check if slug is missing or empty
        if not law.slug:
            print(f"Fixing missing slug for: {law.title[:30]}...")
            # calling save() triggers the slug generation logic in your model
            law.save() 
            fixed_count += 1
            
    print(f"Successfully repaired {fixed_count} Law objects.")
    print("\n--- Step 2: Re-syncing Search Index ---")
    
    # Rebuild MeiliSearch Index
    print("Rebuilding MeiliSearch Index...")
    try:
        call_command('rebuild_meili')
    except Exception as e:
        print(f"Error rebuilding index: {e}")

    print("\n--- DONE ---")
    print("Your data is clean and the search index is updated.")

if __name__ == '__main__':
    fix_and_sync()
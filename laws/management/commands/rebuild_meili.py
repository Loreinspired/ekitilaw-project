from django.core.management.base import BaseCommand
from laws.meili_indexer import rebuild_meili_index

class Command(BaseCommand):
    help = "Rebuild Meili index for laws."

    def handle(self, *args, **options):
        count = rebuild_meili_index()
        self.stdout.write(self.style.SUCCESS(f"Indexed {count} docs into Meili."))

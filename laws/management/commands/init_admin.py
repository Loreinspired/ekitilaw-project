"""
Management command to initialize admin user on first deploy.
Usage: python manage.py init_admin
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Initialize admin user from environment variables'

    def handle(self, *args, **options):
        User = get_user_model()

        # Get credentials from environment
        admin_username = os.getenv('DJANGO_ADMIN_USERNAME', 'admin')
        admin_email = os.getenv('DJANGO_ADMIN_EMAIL', 'admin@ekitilaw.com')
        admin_password = os.getenv('DJANGO_ADMIN_PASSWORD', 'changeme123')

        # Check if admin user already exists
        if User.objects.filter(username=admin_username).exists():
            self.stdout.write(
                self.style.WARNING(f'Admin user "{admin_username}" already exists.')
            )
            return

        # Create superuser
        User.objects.create_superuser(
            username=admin_username,
            email=admin_email,
            password=admin_password
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created admin user: {admin_username}'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                'IMPORTANT: Change the default password after first login!'
            )
        )

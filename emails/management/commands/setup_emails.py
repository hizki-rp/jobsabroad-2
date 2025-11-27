from django.core.management.base import BaseCommand
from django.db import connection
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Set up email system with database tables and default templates'

    def handle(self, *args, **options):
        self.stdout.write('Setting up email system...')
        
        try:
            # Run migrations
            self.stdout.write('Running migrations...')
            call_command('migrate', 'emails', verbosity=0)
            
            # Create default templates
            self.stdout.write('Creating default templates...')
            from emails.services import EmailService
            EmailService.create_default_templates()
            
            self.stdout.write(
                self.style.SUCCESS('Email system setup completed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error setting up email system: {str(e)}')
            )





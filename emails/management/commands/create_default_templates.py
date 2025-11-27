from django.core.management.base import BaseCommand
from emails.services import EmailService


class Command(BaseCommand):
    help = 'Create default email templates'

    def handle(self, *args, **options):
        self.stdout.write('Creating default email templates...')
        
        EmailService.create_default_templates()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created default email templates')
        )





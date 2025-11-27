from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = 'Create default user groups'

    def handle(self, *args, **options):
        user_group, created = Group.objects.get_or_create(name='user')
        if created:
            self.stdout.write(self.style.SUCCESS('Created user group'))
        else:
            self.stdout.write(self.style.WARNING('User group already exists'))
        
        admin_group, created = Group.objects.get_or_create(name='admin')
        if created:
            self.stdout.write(self.style.SUCCESS('Created admin group'))
        else:
            self.stdout.write(self.style.WARNING('Admin group already exists'))
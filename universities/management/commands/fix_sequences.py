from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Fix PostgreSQL sequences'

    def handle(self, *args, **options):
        cursor = connection.cursor()
        cursor.execute("SELECT setval('auth_user_id_seq', (SELECT MAX(id) FROM auth_user));")
        self.stdout.write(self.style.SUCCESS('Successfully fixed user sequence'))
import sqlite3
import json
from django.core.management.base import BaseCommand
from universities.models import University

class Command(BaseCommand):
    help = 'Import scholarship data from SQLite database to PostgreSQL (safe version)'

    def add_arguments(self, parser):
        parser.add_argument('--sqlite-path', type=str, default='db.sqlite3', help='Path to SQLite database')

    def handle(self, *args, **options):
        sqlite_path = options['sqlite_path']
        
        try:
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, name, scholarships FROM universities_university WHERE scholarships != '[]' AND scholarships IS NOT NULL")
            rows = cursor.fetchall()
            
            if not rows:
                print('No scholarship data found in SQLite')
                return
            
            print(f'Found {len(rows)} universities with scholarship data in SQLite')
            
            updated_count = 0
            
            for sqlite_id, name, scholarships_json in rows:
                try:
                    scholarships = json.loads(scholarships_json) if scholarships_json else []
                    
                    if not scholarships:
                        continue
                    
                    # Find matching university in PostgreSQL by name
                    pg_uni = University.objects.filter(name__iexact=name).first()
                    if not pg_uni:
                        # Try partial match
                        pg_uni = University.objects.filter(name__icontains=name.split()[0]).first()
                    
                    if pg_uni:
                        pg_uni.scholarships = scholarships
                        pg_uni.save()
                        updated_count += 1
                        print(f'Updated {pg_uni.name}: {len(scholarships)} scholarships')
                    else:
                        print(f'No match found for: {name}')
                        
                except Exception as e:
                    print(f'Error processing university: {e}')
                    continue
            
            conn.close()
            print(f'Successfully imported scholarships for {updated_count} universities')
            
        except Exception as e:
            print(f'Error accessing SQLite: {e}')
import sqlite3
import json
from django.core.management.base import BaseCommand
from universities.models import University

class Command(BaseCommand):
    help = 'Import program data from SQLite database to PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument('--sqlite-path', type=str, default='db.sqlite3', help='Path to SQLite database')

    def handle(self, *args, **options):
        sqlite_path = options['sqlite_path']
        
        try:
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, name, bachelor_programs, masters_programs FROM universities_university WHERE (bachelor_programs != '[]' OR masters_programs != '[]') AND (bachelor_programs IS NOT NULL OR masters_programs IS NOT NULL)")
            rows = cursor.fetchall()
            
            if not rows:
                print('No program data found in SQLite')
                return
            
            print(f'Found {len(rows)} universities with program data in SQLite')
            
            updated_count = 0
            
            for sqlite_id, name, bachelor_json, masters_json in rows:
                try:
                    bachelor_programs = json.loads(bachelor_json) if bachelor_json else []
                    masters_programs = json.loads(masters_json) if masters_json else []
                    
                    if not bachelor_programs and not masters_programs:
                        continue
                    
                    # Find matching university in PostgreSQL by name
                    pg_uni = University.objects.filter(name__iexact=name).first()
                    if not pg_uni:
                        # Try partial match
                        pg_uni = University.objects.filter(name__icontains=name.split()[0]).first()
                    
                    if pg_uni:
                        if bachelor_programs:
                            pg_uni.bachelor_programs = bachelor_programs
                        if masters_programs:
                            pg_uni.masters_programs = masters_programs
                        pg_uni.save()
                        updated_count += 1
                        print(f'Updated {pg_uni.name}: {len(bachelor_programs)} bachelor, {len(masters_programs)} masters')
                    else:
                        print(f'No match found for: {name}')
                        
                except Exception as e:
                    print(f'Error processing university: {e}')
                    continue
            
            conn.close()
            print(f'Successfully imported programs for {updated_count} universities')
            
        except Exception as e:
            print(f'Error accessing SQLite: {e}')
from django.core.management.base import BaseCommand
from universities.models import University
import json

class Command(BaseCommand):
    help = 'Check if university data was properly migrated from SQLite'

    def handle(self, *args, **options):
        universities = University.objects.all()
        
        self.stdout.write(f"Total universities: {universities.count()}")
        
        # Check for empty JSON fields
        empty_bachelor = universities.filter(bachelor_programs=[]).count()
        empty_masters = universities.filter(masters_programs=[]).count()
        empty_scholarships = universities.filter(scholarships=[]).count()
        empty_intakes = universities.filter(intakes=[]).count()
        
        self.stdout.write(f"\nEmpty JSON fields:")
        self.stdout.write(f"Empty bachelor_programs: {empty_bachelor}")
        self.stdout.write(f"Empty masters_programs: {empty_masters}")
        self.stdout.write(f"Empty scholarships: {empty_scholarships}")
        self.stdout.write(f"Empty intakes: {empty_intakes}")
        
        # Show sample of universities with data
        self.stdout.write(f"\nSample universities with data:")
        
        for uni in universities[:5]:
            self.stdout.write(f"\n{uni.name}:")
            self.stdout.write(f"  Bachelor programs: {len(uni.bachelor_programs)}")
            self.stdout.write(f"  Masters programs: {len(uni.masters_programs)}")
            self.stdout.write(f"  Scholarships: {len(uni.scholarships)}")
            self.stdout.write(f"  Intakes: {len(uni.intakes)}")
            
            if uni.bachelor_programs:
                self.stdout.write(f"  Sample bachelor: {uni.bachelor_programs[0] if uni.bachelor_programs else 'None'}")
            if uni.scholarships:
                self.stdout.write(f"  Sample scholarship: {uni.scholarships[0] if uni.scholarships else 'None'}")
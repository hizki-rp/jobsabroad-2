from django.core.management.base import BaseCommand
from universities.models import University

class Command(BaseCommand):
    help = 'Verify that all universities now have real data'

    def handle(self, *args, **options):
        total_universities = University.objects.count()
        
        # Count universities with empty data
        empty_bachelor = University.objects.filter(bachelor_programs=[]).count()
        empty_masters = University.objects.filter(masters_programs=[]).count()
        empty_scholarships = University.objects.filter(scholarships=[]).count()
        empty_intakes = University.objects.filter(intakes=[]).count()
        
        self.stdout.write(f'Total universities: {total_universities}')
        self.stdout.write('')
        self.stdout.write('Universities with empty data:')
        self.stdout.write(f'  Empty bachelor_programs: {empty_bachelor}')
        self.stdout.write(f'  Empty masters_programs: {empty_masters}')
        self.stdout.write(f'  Empty scholarships: {empty_scholarships}')
        self.stdout.write(f'  Empty intakes: {empty_intakes}')
        self.stdout.write('')
        
        # Show sample of populated data
        populated_unis = University.objects.exclude(bachelor_programs=[])[:5]
        
        self.stdout.write('Sample universities with data:')
        for uni in populated_unis:
            self.stdout.write(f'  {uni.name} ({uni.country}):')
            self.stdout.write(f'    Bachelor programs: {len(uni.bachelor_programs)}')
            self.stdout.write(f'    Masters programs: {len(uni.masters_programs)}')
            self.stdout.write(f'    Scholarships: {len(uni.scholarships)}')
            self.stdout.write(f'    Intakes: {len(uni.intakes)}')
            self.stdout.write('')
        
        if empty_bachelor == 0 and empty_masters == 0 and empty_scholarships == 0 and empty_intakes == 0:
            self.stdout.write(self.style.SUCCESS('✓ All universities now have complete data!'))
        else:
            self.stdout.write(self.style.WARNING(f'Some universities still need data recovery'))
from django.core.management.base import BaseCommand
from universities.models import University

class Command(BaseCommand):
    help = 'Fix intake formats to remove years and show only months'

    def handle(self, *args, **options):
        universities = University.objects.all()
        updated_count = 0
        
        for uni in universities:
            if uni.intakes:
                updated_intakes = []
                for intake in uni.intakes:
                    # Clean up intake format
                    name = intake.get('name', '')
                    deadline = intake.get('application_deadline', '')
                    deposit_deadline = intake.get('deposit_deadline', '')
                    
                    # Remove years and specific dates, keep only months
                    if deadline:
                        deadline = deadline.split()[0] if deadline else ''  # Get first word (month)
                    if deposit_deadline:
                        deposit_deadline = deposit_deadline.split()[0] if deposit_deadline else ''
                    
                    # Update intake format
                    updated_intake = {
                        'name': name,
                        'application_deadline': deadline,
                        'deposit_deadline': deposit_deadline
                    }
                    updated_intakes.append(updated_intake)
                
                uni.intakes = updated_intakes
                uni.save()
                updated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Updated intake formats for {updated_count} universities')
        )
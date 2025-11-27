import requests
from django.core.management.base import BaseCommand
from universities.models import University

class Command(BaseCommand):
    help = 'Fetch real scholarships from ScholarshipOwl API'

    def add_arguments(self, parser):
        parser.add_argument('--api-key', type=str, required=True, help='ScholarshipOwl API key')
        parser.add_argument('--limit', type=int, default=50, help='Number of scholarships to fetch')

    def handle(self, *args, **options):
        api_key = options['api_key']
        limit = options['limit']
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Fetch scholarships from ScholarshipOwl API
            response = requests.get(
                'https://api.scholarshipowl.com/v1/scholarships',
                headers=headers,
                params={'limit': limit}
            )
            
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f'API Error: {response.status_code} - {response.text}'))
                return
            
            scholarships_data = response.json()
            scholarships = scholarships_data.get('data', [])
            
            if not scholarships:
                self.stdout.write(self.style.WARNING('No scholarships found'))
                return
            
            self.stdout.write(f'Found {len(scholarships)} scholarships')
            
            # Update universities with real scholarship data
            universities = University.objects.all()
            updated_count = 0
            
            for uni in universities:
                # Filter scholarships by country if possible
                country_scholarships = [
                    s for s in scholarships 
                    if uni.country.lower() in s.get('eligibility', '').lower() or
                       uni.country.lower() in s.get('description', '').lower()
                ][:3]
                
                # If no country-specific scholarships, use general ones
                if not country_scholarships:
                    country_scholarships = scholarships[:3]
                
                # Format scholarships for our model
                formatted_scholarships = []
                for scholarship in country_scholarships:
                    formatted_scholarships.append({
                        'name': scholarship.get('title', 'Scholarship'),
                        'coverage': scholarship.get('amount', 'Varies'),
                        'eligibility': scholarship.get('eligibility', 'See requirements'),
                        'link': scholarship.get('url', '')
                    })
                
                uni.scholarships = formatted_scholarships
                uni.save()
                updated_count += 1
                
                if updated_count % 10 == 0:
                    self.stdout.write(f'Updated {updated_count} universities...')
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated {updated_count} universities with real scholarships')
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error fetching scholarships: {str(e)}'))
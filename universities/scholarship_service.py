import requests
from django.conf import settings

class ScholarshipOwlService:
    BASE_URL = 'https://api.scholarshipowl.com/v1'
    
    def __init__(self, api_key=None):
        self.api_key = api_key or getattr(settings, 'SCHOLARSHIPOWL_API_KEY', None)
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def get_scholarships(self, country=None, limit=10):
        """Fetch scholarships, optionally filtered by country"""
        params = {'limit': limit}
        if country:
            params['country'] = country
            
        response = requests.get(
            f'{self.BASE_URL}/scholarships',
            headers=self.headers,
            params=params
        )
        
        if response.status_code == 200:
            return response.json().get('data', [])
        return []
    
    def format_for_university(self, scholarships):
        """Format scholarships for University model"""
        return [
            {
                'name': s.get('title', 'Scholarship'),
                'coverage': s.get('amount', 'Varies'),
                'eligibility': s.get('eligibility', 'See requirements'),
                'link': s.get('url', '')
            }
            for s in scholarships[:5]  # Limit to 5 per university
        ]
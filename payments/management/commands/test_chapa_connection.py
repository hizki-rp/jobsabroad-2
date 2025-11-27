from django.core.management.base import BaseCommand
import os
import requests
import json

class Command(BaseCommand):
    help = 'Test Chapa production connection and configuration'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing Chapa Production Configuration...'))
        
        # Check environment variables
        chapa_secret = os.environ.get("CHAPA_SECRET_KEY")
        webhook_secret = os.environ.get("CHAPA_WEBHOOK_SECRET")
        backend_url = os.environ.get("BACKEND_URL")
        frontend_url = os.environ.get("FRONTEND_URL")
        
        self.stdout.write('\n=== Environment Variables ===')
        self.stdout.write(f'CHAPA_SECRET_KEY: {"[OK] Set" if chapa_secret else "[MISSING]"}')
        if chapa_secret:
            self.stdout.write(f'  Key starts with: {chapa_secret[:15]}...')
            self.stdout.write(f'  Is production key: {"[OK] Yes" if not "TEST" in chapa_secret else "[ERROR] No (Test key)"}')
        
        self.stdout.write(f'CHAPA_WEBHOOK_SECRET: {"[OK] Set" if webhook_secret else "[MISSING]"}')
        self.stdout.write(f'BACKEND_URL: {backend_url or "[MISSING]"}')
        self.stdout.write(f'FRONTEND_URL: {frontend_url or "[MISSING]"}')
        
        if not chapa_secret:
            self.stdout.write(self.style.ERROR('Cannot proceed without CHAPA_SECRET_KEY'))
            return
        
        # Test webhook URL accessibility
        self.stdout.write('\n=== Webhook URL Test ===')
        if backend_url:
            webhook_url = f"{backend_url.rstrip('/')}/api/chapa-webhook/"
            self.stdout.write(f'Testing webhook URL: {webhook_url}')
            
            try:
                response = requests.get(webhook_url, timeout=30)
                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS('[OK] Webhook URL is accessible'))
                else:
                    self.stdout.write(self.style.WARNING(f'[WARNING] Webhook returned status: {response.status_code}'))
            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f'[ERROR] Webhook URL not accessible: {e}'))
        
        # Test Chapa API connection
        self.stdout.write('\n=== Chapa API Test ===')
        headers = {
            "Authorization": f"Bearer {chapa_secret}",
            "Content-Type": "application/json"
        }
        
        # Test with minimal payload
        test_payload = {
            "amount": 1,
            "currency": "ETB",
            "email": "testuser@gmail.com",
            "first_name": "Test",
            "last_name": "User",
            "tx_ref": f"test-{os.urandom(8).hex()}",
            "callback_url": f"{backend_url}/api/chapa-webhook/" if backend_url else "https://example.com/webhook",
            "return_url": f"{frontend_url}/payment-success" if frontend_url else "https://example.com/success",
        }
        
        try:
            self.stdout.write('Sending test request to Chapa...')
            response = requests.post(
                "https://api.chapa.co/v1/transaction/initialize",
                headers=headers,
                json=test_payload,
                timeout=30
            )
            
            self.stdout.write(f'Response Status: {response.status_code}')
            
            try:
                response_data = response.json()
                self.stdout.write(f'Response Data: {json.dumps(response_data, indent=2)}')
                
                if response.status_code == 200 and response_data.get('status') == 'success':
                    self.stdout.write(self.style.SUCCESS('[OK] Chapa API connection successful'))
                    checkout_url = response_data.get('data', {}).get('checkout_url')
                    if checkout_url:
                        self.stdout.write(f'Test checkout URL: {checkout_url}')
                else:
                    self.stdout.write(self.style.ERROR('[ERROR] Chapa API returned error'))
                    if 'message' in response_data:
                        self.stdout.write(f'Error message: {response_data["message"]}')
                        
            except json.JSONDecodeError:
                self.stdout.write(f'Raw response: {response.text}')
                
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Failed to connect to Chapa API: {e}'))
        
        # Common issues and solutions
        self.stdout.write('\n=== Common Production Issues ===')
        self.stdout.write('1. Webhook URL must be publicly accessible (not localhost)')
        self.stdout.write('2. Production secret key must be activated in Chapa dashboard')
        self.stdout.write('3. Domain must be whitelisted in Chapa settings')
        self.stdout.write('4. SSL certificate must be valid for webhook URL')
        self.stdout.write('5. Check Chapa dashboard for any account restrictions')
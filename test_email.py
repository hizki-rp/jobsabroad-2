#!/usr/bin/env python
"""
Test email configuration
Run this script to test if emails are being sent properly
"""

import os
import sys
import django
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'university_api.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

def test_email():
    """Test email sending functionality"""
    print("Testing email configuration...")
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print()
    
    try:
        # Test sending an email
        subject = 'Test Email from Addis Temari'
        message = '''
        Hello!
        
        This is a test email from the Addis Temari system.
        
        If you receive this email, the email configuration is working correctly!
        
        Best regards,
        Addis Temari Team
        '''
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = ['addistemari.m@gmail.com']  # Send to yourself for testing
        
        print(f"Sending test email to: {recipient_list[0]}")
        result = send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        
        if result:
            print("✅ Email sent successfully!")
            print("Check your inbox for the test email.")
        else:
            print("❌ Email sending failed")
            
    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Make sure the Gmail app password is correct")
        print("2. Ensure 2-factor authentication is enabled on the Gmail account")
        print("3. Check that 'Less secure app access' is enabled (if not using app passwords)")
        print("4. Verify the Gmail account is not locked or restricted")

if __name__ == "__main__":
    test_email()


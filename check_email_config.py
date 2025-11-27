#!/usr/bin/env python
"""
Check email configuration and test sending
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

from django.conf import settings
from django.core.mail import send_mail
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def check_email_config():
    """Check email configuration"""
    print("=== Email Configuration Check ===")
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_USE_SSL: {getattr(settings, 'EMAIL_USE_SSL', False)}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"EMAIL_HOST_PASSWORD: {'*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 'Not set'}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print(f"EMAIL_TIMEOUT: {getattr(settings, 'EMAIL_TIMEOUT', 'Not set')}")
    print()

def test_smtp_connection():
    """Test SMTP connection directly"""
    print("=== Testing SMTP Connection ===")
    try:
        # Create SMTP connection
        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        server.starttls()  # Enable TLS
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        print("✅ SMTP connection successful!")
        server.quit()
        return True
    except Exception as e:
        print(f"❌ SMTP connection failed: {str(e)}")
        return False

def test_django_email():
    """Test Django email sending"""
    print("=== Testing Django Email Sending ===")
    try:
        result = send_mail(
            subject='Test Email from Addis Temari',
            message='This is a test email to verify email configuration.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['addistemari.m@gmail.com'],
            fail_silently=False,
        )
        
        if result:
            print("✅ Django email sending successful!")
            return True
        else:
            print("❌ Django email sending returned False")
            return False
            
    except Exception as e:
        print(f"❌ Django email sending failed: {str(e)}")
        return False

def main():
    """Main function"""
    print("Addis Temari Email Configuration Test")
    print("=" * 50)
    
    # Check configuration
    check_email_config()
    
    # Test SMTP connection
    smtp_ok = test_smtp_connection()
    print()
    
    # Test Django email
    django_ok = test_django_email()
    print()
    
    # Summary
    print("=== Summary ===")
    if smtp_ok and django_ok:
        print("✅ All email tests passed! Email configuration is working correctly.")
    elif smtp_ok and not django_ok:
        print("⚠️  SMTP connection works but Django email sending failed.")
        print("   Check Django email settings and try again.")
    elif not smtp_ok:
        print("❌ SMTP connection failed. Check your Gmail credentials and settings.")
        print("   Make sure:")
        print("   1. Gmail app password is correct")
        print("   2. 2-factor authentication is enabled")
        print("   3. App password was generated correctly")
        print("   4. Gmail account is not locked")
    else:
        print("❌ Email configuration has issues.")

if __name__ == "__main__":
    main()


#!/usr/bin/env python
"""
Script to find and fix stuck payments by email
Usage: python fix_stuck_payment.py <email>
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'university_api.settings')
django.setup()

from django.contrib.auth.models import User
from payments.models import Payment
from universities.models import UserDashboard
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

def fix_by_email(email):
    """Find user by email and check/fix their subscription"""
    
    print(f"\n🔍 Looking for user with email: {email}")
    print("=" * 60)
    
    try:
        user = User.objects.filter(email=email).first()
        
        if not user:
            print(f"❌ No user found with email: {email}")
            return False
        
        print(f"✅ Found user: {user.username} (ID: {user.id})")
        
        # Check for payments
        payments = Payment.objects.filter(user=user).order_by('-payment_date')
        
        print(f"\n💳 Payments for this user:")
        if not payments.exists():
            print("   No payments found")
        else:
            for payment in payments:
                print(f"\n   Payment ID: {payment.id}")
                print(f"   TX Ref: {payment.tx_ref}")
                print(f"   Amount: {payment.amount}")
                print(f"   Status: {payment.status}")
                print(f"   Date: {payment.payment_date}")
                print(f"   Subscription Updated: {payment.subscription_updated}")
        
        # Check dashboard
        dashboard, created = UserDashboard.objects.get_or_create(user=user)
        
        print(f"\n📊 Current Dashboard Status:")
        print(f"   Subscription Status: {dashboard.subscription_status}")
        print(f"   End Date: {dashboard.subscription_end_date}")
        print(f"   Is Verified: {dashboard.is_verified}")
        print(f"   Total Paid: {dashboard.total_paid}")
        print(f"   Months Subscribed: {dashboard.months_subscribed}")
        
        # Find unprocessed successful payments
        unprocessed = payments.filter(status='success', subscription_updated=False)
        
        if unprocessed.exists():
            print(f"\n⚠️  Found {unprocessed.count()} unprocessed payment(s)!")
            
            for payment in unprocessed:
                print(f"\n🔄 Processing payment: {payment.tx_ref}")
                
                dashboard.total_paid = Decimal(str(dashboard.total_paid)) + Decimal(str(payment.amount))
                dashboard.months_subscribed += 1
                dashboard.subscription_status = 'active'
                dashboard.is_verified = True
                
                if not dashboard.subscription_end_date or dashboard.subscription_end_date < timezone.now().date():
                    dashboard.subscription_end_date = timezone.now().date() + timedelta(days=30)
                else:
                    dashboard.subscription_end_date = dashboard.subscription_end_date + timedelta(days=30)
                
                dashboard.save()
                
                payment.subscription_updated = True
                payment.save()
                
                print(f"   ✅ Updated subscription!")
            
            print(f"\n📊 Updated Dashboard Status:")
            print(f"   Subscription Status: {dashboard.subscription_status}")
            print(f"   End Date: {dashboard.subscription_end_date}")
            print(f"   Is Verified: {dashboard.is_verified}")
            print(f"   Total Paid: {dashboard.total_paid}")
            print(f"   Months Subscribed: {dashboard.months_subscribed}")
            
            return True
        else:
            if payments.filter(status='success').exists():
                print(f"\n✅ All payments already processed")
            else:
                print(f"\n⚠️  No successful payments found")
            return True
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_stuck_payment.py <email>")
        print("\nExample:")
        print("  python fix_stuck_payment.py zumimes@mailinator.com")
        sys.exit(1)
    
    email = sys.argv[1]
    success = fix_by_email(email)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ DONE - Check results above")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ FAILED")
        print("=" * 60)
        sys.exit(1)

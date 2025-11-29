#!/usr/bin/env python
"""
Manual script to verify a payment with Chapa and update subscription.
Usage: python manual_verify_payment.py <tx_ref>
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'university_api.settings')
django.setup()

import requests
from django.contrib.auth.models import User
from payments.models import Payment
from universities.models import UserDashboard
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

def verify_and_update(tx_ref):
    """Verify payment with Chapa and update subscription"""
    
    chapa_secret_key = os.environ.get("CHAPA_SECRET_KEY")
    if not chapa_secret_key:
        print("❌ CHAPA_SECRET_KEY not found in environment")
        return False
    
    print(f"\n🔍 Verifying payment: {tx_ref}")
    print("=" * 60)
    
    try:
        # Verify with Chapa API
        verify_url = f"https://api.chapa.co/v1/transaction/verify/{tx_ref}"
        headers = {"Authorization": f"Bearer {chapa_secret_key}"}
        
        print(f"📡 Calling Chapa API: {verify_url}")
        verify_response = requests.get(verify_url, headers=headers)
        verify_data = verify_response.json()
        
        print(f"\n📥 Chapa Response:")
        print(f"  Status: {verify_data.get('status')}")
        print(f"  Message: {verify_data.get('message')}")
        
        if verify_data.get('data'):
            data = verify_data['data']
            print(f"  Transaction Status: {data.get('status')}")
            print(f"  Amount: {data.get('amount')} {data.get('currency')}")
            print(f"  Email: {data.get('email')}")
            print(f"  First Name: {data.get('first_name')}")
            print(f"  Last Name: {data.get('last_name')}")
        
        # Check if payment was successful
        if verify_data.get('status') != 'success':
            print(f"\n❌ Chapa verification failed: {verify_data.get('message')}")
            return False
        
        payment_data = verify_data.get('data', {})
        if payment_data.get('status') != 'success':
            print(f"\n❌ Payment status is not 'success': {payment_data.get('status')}")
            return False
        
        print(f"\n✅ Payment verified successfully with Chapa!")
        
        # Extract user from tx_ref
        user = None
        if tx_ref.startswith('unifinder-'):
            parts = tx_ref.split('-')
            if len(parts) >= 2:
                try:
                    user_id = int(parts[1])
                    user = User.objects.get(id=user_id)
                    print(f"\n👤 User found: {user.username} (ID: {user_id}, Email: {user.email})")
                except (ValueError, User.DoesNotExist) as e:
                    print(f"\n❌ Could not find user from tx_ref: {e}")
        
        if not user:
            # Try to find by email from payment data
            email = payment_data.get('email')
            if email:
                user = User.objects.filter(email=email).first()
                if user:
                    print(f"\n👤 User found by email: {user.username} (Email: {user.email})")
        
        if not user:
            print(f"\n❌ Could not identify user from tx_ref or email")
            return False
        
        # Get or create payment record
        payment, created = Payment.objects.get_or_create(
            tx_ref=tx_ref,
            defaults={
                'user': user,
                'amount': Decimal('500.00'),
                'status': 'success',
                'payment_date': timezone.now(),
                'chapa_reference': payment_data.get('reference', '')
            }
        )
        
        if created:
            print(f"\n💳 Created new payment record")
        else:
            print(f"\n💳 Found existing payment record")
            if payment.status != 'success':
                payment.status = 'success'
                payment.save()
                print(f"   Updated status to 'success'")
        
        print(f"   Payment ID: {payment.id}")
        print(f"   Amount: {payment.amount}")
        print(f"   Status: {payment.status}")
        print(f"   Subscription Updated: {payment.subscription_updated}")
        
        # Update subscription
        dashboard, _ = UserDashboard.objects.get_or_create(user=user)
        
        print(f"\n📊 Current Dashboard Status:")
        print(f"   Subscription Status: {dashboard.subscription_status}")
        print(f"   End Date: {dashboard.subscription_end_date}")
        print(f"   Is Verified: {dashboard.is_verified}")
        print(f"   Total Paid: {dashboard.total_paid}")
        print(f"   Months Subscribed: {dashboard.months_subscribed}")
        
        if not payment.subscription_updated:
            print(f"\n🔄 Updating subscription...")
            
            dashboard.total_paid = Decimal(str(dashboard.total_paid)) + Decimal('500.00')
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
            
            print(f"\n✅ Subscription Updated Successfully!")
            print(f"   New Status: {dashboard.subscription_status}")
            print(f"   New End Date: {dashboard.subscription_end_date}")
            print(f"   New Total Paid: {dashboard.total_paid}")
            print(f"   New Months Subscribed: {dashboard.months_subscribed}")
            
            return True
        else:
            print(f"\n⚠️  Payment already processed (subscription_updated=True)")
            print(f"   Current Status: {dashboard.subscription_status}")
            print(f"   Current End Date: {dashboard.subscription_end_date}")
            return True
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manual_verify_payment.py <tx_ref>")
        print("\nExample:")
        print("  python manual_verify_payment.py unifinder-24-abc123")
        sys.exit(1)
    
    tx_ref = sys.argv[1]
    success = verify_and_update(tx_ref)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ SUCCESS - Subscription has been updated!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ FAILED - Could not update subscription")
        print("=" * 60)
        sys.exit(1)

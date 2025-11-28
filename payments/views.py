from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from .models import Payment
from django.db.models import Sum, Count
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

@api_view(['POST'])
@permission_classes([AllowAny])
def initialize_payment(request):
    """Initializes a payment, allowing anonymous access."""
    # Your logic to handle payment initialization
    return Response({"message": "Payment initialization successful."})

@api_view(['GET'])
@permission_classes([IsAdminUser])
def recent_payments(request):
    """Get recent payments - admin only"""
    days = int(request.GET.get('days', 1))
    
    # Calculate date range
    now = timezone.now()
    start_date = now - timedelta(days=days)
    
    # Get recent payments
    payments = Payment.objects.filter(
        payment_date__gte=start_date
    ).select_related('user').order_by('-payment_date')
    
    # Format payment data
    payment_data = []
    for payment in payments:
        payment_data.append({
            'id': payment.id,
            'user': {
                'id': payment.user.id,
                'username': payment.user.username,
                'email': payment.user.email,
                'first_name': payment.user.first_name,
                'last_name': payment.user.last_name,
            },
            'amount': str(payment.amount),
            'status': payment.status,
            'payment_date': payment.payment_date.isoformat(),
            'tx_ref': payment.tx_ref,
            'chapa_reference': payment.chapa_reference,
        })
    
    # Calculate statistics
    successful_payments = payments.filter(status='success')
    total_amount = successful_payments.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get unique users
    unique_users = payments.values(
        'user__id', 'user__username', 'user__email'
    ).distinct()
    
    return Response({
        'period': f'Last {days} day(s)',
        'start_date': start_date.isoformat(),
        'end_date': now.isoformat(),
        'total_payments': payments.count(),
        'successful_payments': successful_payments.count(),
        'total_amount': str(total_amount),
        'unique_users_count': len(unique_users),
        'unique_users': list(unique_users),
        'payments': payment_data
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_payment(request):
    """Confirm payment and return auth tokens for auto-login"""
    tx_ref = request.data.get('tx_ref') or request.data.get('payment_ref')
    draft_id = request.data.get('draft_id')
    email = request.data.get('email')
    
    print(f"=== CONFIRM PAYMENT CALLED ===")
    print(f"  tx_ref: {tx_ref}")
    print(f"  draft_id: {draft_id}")
    print(f"  email: {email}")
    
    try:
        # Find the payment - check for any payment with this tx_ref first
        payment = Payment.objects.filter(tx_ref=tx_ref).first() if tx_ref else None
        user = None
        
        if payment:
            user = payment.user
            print(f"Found existing payment for user: {user.username if user else 'None'}")
            # If payment exists but status is not 'success', update it
            if payment.status != 'success':
                payment.status = 'success'
                payment.save()
                print(f"Updated payment {tx_ref} status to 'success' during confirmation")
        else:
            print(f"No existing payment found for tx_ref: {tx_ref}")
            
            # FIRST: Try to extract user ID from tx_ref format: "unifinder-{user_id}-{uuid}"
            if tx_ref and tx_ref.startswith('unifinder-'):
                try:
                    parts = tx_ref.split('-')
                    if len(parts) >= 2:
                        user_id = int(parts[1])
                        user = User.objects.get(id=user_id)
                        print(f"Extracted user {user.username} (ID: {user_id}) from tx_ref: {tx_ref}")
                except (IndexError, ValueError, User.DoesNotExist) as e:
                    print(f"Could not extract user from tx_ref: {tx_ref}, error: {e}")
            
            # SECOND: Try draft_id
            if not user and draft_id:
                from universities.models import ApplicationDraft
                try:
                    draft = ApplicationDraft.objects.get(id=draft_id)
                    user = draft.user if hasattr(draft, 'user') else None
                    if not user:
                        user = User.objects.filter(email=draft.email).first()
                    if user:
                        print(f"Found user {user.username} from draft_id: {draft_id}")
                    if user and draft.payment_tx_ref and not tx_ref:
                        tx_ref = draft.payment_tx_ref
                        print(f"Using tx_ref from draft: {tx_ref}")
                except Exception as e:
                    print(f"Error finding user from draft_id: {e}")
            
            # THIRD: Try email
            if not user and email:
                user = User.objects.filter(email=email).first()
                if user:
                    print(f"Found user {user.username} from email: {email}")
                    if not tx_ref:
                        # Generate a tx_ref for this payment
                        import uuid
                        tx_ref = f"payment_{user.id}_{uuid.uuid4().hex[:8]}"
                        print(f"Generated tx_ref for user {user.email}: {tx_ref}")
            
            if not user:
                print(f"ERROR: Could not identify user from tx_ref={tx_ref}, draft_id={draft_id}, email={email}")
                return Response(
                    {'error': 'Could not identify user. Please try logging in first.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create payment record if it doesn't exist
            if not tx_ref:
                import uuid
                tx_ref = f"payment_{user.id}_{uuid.uuid4().hex[:8]}"
            
            payment = Payment.objects.filter(tx_ref=tx_ref).first()
            if not payment:
                payment = Payment.objects.create(
                    user=user,
                    amount=500.00,
                    tx_ref=tx_ref,
                    status='success',
                    payment_date=timezone.now()
                )
                print(f"Created payment record {tx_ref} for user {user.username} during confirmation")
            else:
                # Payment exists but wasn't linked to user initially
                if payment.status != 'success':
                    payment.status = 'success'
                    payment.save()
                    print(f"Updated existing payment {tx_ref} to success")
        
        # Ensure subscription is updated (only if this payment hasn't been processed yet)
        from universities.models import UserDashboard
        from django.utils import timezone
        from datetime import timedelta
        
        dashboard, _ = UserDashboard.objects.get_or_create(user=user)
        
        # Refresh dashboard and payment to get latest state
        dashboard.refresh_from_db()
        if payment:
            payment.refresh_from_db()
        
        print(f"Payment confirmation for user {user.username}:")
        print(f"  - Before update: status={dashboard.subscription_status}, end_date={dashboard.subscription_end_date}")
        print(f"  - Payment amount: {payment.amount if payment else 500.00}")
        print(f"  - Payment subscription_updated: {payment.subscription_updated if payment else 'N/A'}")
        
        # Only update subscription if this payment hasn't been processed yet
        if payment and not payment.subscription_updated:
            try:
                amount = payment.amount
                print(f"  Calling update_subscription with amount: {amount}")
                
                months_added = dashboard.update_subscription(amount, monthly_price=500)
                
                # Mark payment as processed
                payment.subscription_updated = True
                payment.save()
                print(f"  Marked payment as processed (subscription_updated=True)")
                
                # Refresh after update_subscription
                dashboard.refresh_from_db()
                print(f"  After update_subscription: months_added={months_added}")
                print(f"  Result: status={dashboard.subscription_status}, end_date={dashboard.subscription_end_date}")
                print(f"  Result: total_paid={dashboard.total_paid}, months_subscribed={dashboard.months_subscribed}, is_verified={dashboard.is_verified}")
                
            except Exception as e:
                print(f"Error in update_subscription: {e}")
                import traceback
                traceback.print_exc()
                
                # Fallback - directly set all fields without calling update_subscription
                from decimal import Decimal
                amount = Decimal(str(payment.amount)) if payment else Decimal('500.00')
                
                dashboard.total_paid = Decimal(str(dashboard.total_paid)) + amount
                dashboard.months_subscribed += 1
                dashboard.subscription_status = 'active'
                dashboard.is_verified = True
                
                if not dashboard.subscription_end_date or dashboard.subscription_end_date < timezone.now().date():
                    dashboard.subscription_end_date = timezone.now().date() + timedelta(days=30)
                else:
                    dashboard.subscription_end_date = dashboard.subscription_end_date + timedelta(days=30)
                
                dashboard.save()
                
                # Mark payment as processed even in fallback
                payment.subscription_updated = True
                payment.save()
                
                print(f"Used fallback to activate subscription for user {user.username}")
                print(f"Fallback result: status={dashboard.subscription_status}, end_date={dashboard.subscription_end_date}")
        else:
            print(f"  Payment already processed (subscription_updated=True), skipping update")
            # Ensure subscription is active anyway
            if dashboard.subscription_status != 'active':
                dashboard.subscription_status = 'active'
                dashboard.is_verified = True
                if not dashboard.subscription_end_date:
                    dashboard.subscription_end_date = timezone.now().date() + timedelta(days=30)
                dashboard.save()
                print(f"  Fixed subscription status to active")
        
        # Ensure is_verified is set
        if not dashboard.is_verified:
            dashboard.is_verified = True
            dashboard.save()
        
        # Generate JWT tokens for auto-login
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'status': 'success',
            'message': 'Payment confirmed',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'token': str(refresh.access_token),  # For backward compatibility
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'name': f"{user.first_name} {user.last_name}".strip() or user.username
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Error confirming payment: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAdminUser])
def todays_payments(request):
    """Get today's payments specifically"""
    today = timezone.now().date()
    start_of_day = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    end_of_day = start_of_day + timedelta(days=1)
    
    payments = Payment.objects.filter(
        payment_date__gte=start_of_day,
        payment_date__lt=end_of_day
    ).select_related('user').order_by('-payment_date')
    
    payment_data = []
    for payment in payments:
        payment_data.append({
            'id': payment.id,
            'user': {
                'id': payment.user.id,
                'username': payment.user.username,
                'email': payment.user.email,
                'first_name': payment.user.first_name,
                'last_name': payment.user.last_name,
            },
            'amount': str(payment.amount),
            'status': payment.status,
            'payment_date': payment.payment_date.isoformat(),
            'tx_ref': payment.tx_ref,
        })
    
    successful_today = payments.filter(status='success')
    total_today = successful_today.aggregate(Sum('amount'))['amount__sum'] or 0
    
    return Response({
        'date': today.isoformat(),
        'total_payments': payments.count(),
        'successful_payments': successful_today.count(),
        'total_amount': str(total_today),
        'payments': payment_data
    })
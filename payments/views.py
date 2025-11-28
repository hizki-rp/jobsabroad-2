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
    
    if not tx_ref:
        return Response(
            {'error': 'Transaction reference (tx_ref) is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Find the payment - check for any payment with this tx_ref first
        payment = Payment.objects.filter(tx_ref=tx_ref).first()
        
        # If payment doesn't exist, try to find user from draft_id or create payment
        user = None
        if payment:
            user = payment.user
            # If payment exists but status is not 'success', update it
            if payment.status != 'success':
                payment.status = 'success'
                payment.save()
                print(f"Updated payment {tx_ref} status to 'success' during confirmation")
        else:
            # Payment doesn't exist - try to find user from draft_id
            if draft_id:
                from universities.models import ApplicationDraft
                try:
                    draft = ApplicationDraft.objects.get(id=draft_id)
                    user = draft.user if hasattr(draft, 'user') else None
                    if not user:
                        # Try to find user by email
                        from django.contrib.auth.models import User
                        user = User.objects.filter(email=draft.email).first()
                    
                    if user:
                        # Create payment record
                        payment = Payment.objects.create(
                            user=user,
                            amount=500.00,
                            tx_ref=tx_ref,
                            status='success'
                        )
                        print(f"Created payment record {tx_ref} for user {user.username} during confirmation")
                except Exception as e:
                    print(f"Error finding user from draft_id: {e}")
        
        if not user:
            return Response(
                {'error': 'Payment not found and unable to determine user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Ensure subscription is updated (in case webhook hasn't processed yet)
        from universities.models import UserDashboard
        from django.utils import timezone
        from datetime import timedelta
        
        dashboard, _ = UserDashboard.objects.get_or_create(user=user)
        
        # Always update subscription when payment is confirmed
        # Ensure both status and end_date are set
        try:
            amount = payment.amount if payment else 500.00
            months_added = dashboard.update_subscription(amount, monthly_price=500)
            
            # Ensure subscription is active and end_date is set (even if months_added is 0)
            if dashboard.subscription_status != 'active' or not dashboard.subscription_end_date:
                dashboard.subscription_status = 'active'
                if not dashboard.subscription_end_date:
                    dashboard.subscription_end_date = timezone.now().date() + timedelta(days=30)
                elif dashboard.subscription_end_date < timezone.now().date():
                    # If expired, extend from today
                    dashboard.subscription_end_date = timezone.now().date() + timedelta(days=30)
                else:
                    # If active, extend from current end date
                    dashboard.subscription_end_date += timedelta(days=30)
            
            dashboard.is_verified = True
            dashboard.save()
            print(f"Payment confirmed: {months_added} months added for user {user.username}. Subscription status: {dashboard.subscription_status}, End date: {dashboard.subscription_end_date}")
        except Exception as e:
            print(f"Error updating subscription: {e}")
            import traceback
            traceback.print_exc()
            # Fallback - ensure subscription is activated with proper end date
            dashboard.subscription_status = 'active'
            if not dashboard.subscription_end_date or dashboard.subscription_end_date < timezone.now().date():
                dashboard.subscription_end_date = timezone.now().date() + timedelta(days=30)
            else:
                dashboard.subscription_end_date += timedelta(days=30)
            dashboard.is_verified = True
            dashboard.save()
            print(f"Used fallback to activate subscription for user {user.username}. End date: {dashboard.subscription_end_date}")
        
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
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
        user = None
        payment = None
        
        # Try to find user from tx_ref format: "unifinder-{user_id}-{uuid}"
        if tx_ref and tx_ref.startswith('unifinder-'):
            try:
                user_id = int(tx_ref.split('-')[1])
                user = User.objects.get(id=user_id)
                print(f"Found user {user.username} (ID: {user_id}) from tx_ref")
            except (IndexError, ValueError, User.DoesNotExist) as e:
                print(f"Could not extract user from tx_ref: {tx_ref}, error: {e}")
        
        # Try email as fallback
        if not user and email:
            user = User.objects.filter(email=email).first()
            if user:
                print(f"Found user {user.username} from email: {email}")
        
        if not user:
            print(f"ERROR: Could not identify user")
            return Response(
                {'error': 'Could not identify user. Please try logging in first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check for existing payment or create one
        if tx_ref:
            payment = Payment.objects.filter(tx_ref=tx_ref).first()
        
        if not payment:
            # Generate tx_ref if not provided
            if not tx_ref:
                import uuid
                tx_ref = f"payment_{user.id}_{uuid.uuid4().hex[:8]}"
            
            payment = Payment.objects.create(
                user=user,
                amount=500.00,
                tx_ref=tx_ref,
                status='success',
                payment_date=timezone.now()
            )
            print(f"Created payment record {tx_ref} for user {user.username}")
        else:
            # Update payment status if needed
            if payment.status != 'success':
                payment.status = 'success'
                payment.save()
                print(f"Updated payment {tx_ref} status to success")
        
        # Update subscription
        from universities.models import UserDashboard
        dashboard, _ = UserDashboard.objects.get_or_create(user=user)
        
        print(f"Before update: status={dashboard.subscription_status}, end_date={dashboard.subscription_end_date}")
        
        # Always update subscription when payment is confirmed
        try:
            months_added = dashboard.update_subscription(500.00, monthly_price=500)
            print(f"Subscription updated: {months_added} months added")
        except Exception as e:
            print(f"Error in update_subscription: {e}")
            # Fallback - direct update
            dashboard.subscription_status = 'active'
            dashboard.subscription_end_date = timezone.now().date() + timedelta(days=30)
            dashboard.is_verified = True
            dashboard.save()
            print(f"Used fallback to activate subscription")
        
        dashboard.refresh_from_db()
        print(f"After update: status={dashboard.subscription_status}, end_date={dashboard.subscription_end_date}")
        
        # Generate JWT tokens for auto-login
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'status': 'success',
            'message': 'Payment confirmed',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'token': str(refresh.access_token),
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
        print(f"Error in confirm_payment: {e}")
        import traceback
        traceback.print_exc()
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
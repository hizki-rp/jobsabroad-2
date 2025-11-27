from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from .models import Payment
from django.db.models import Sum, Count

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
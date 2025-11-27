from django.contrib import admin
from django.db.models import Sum, Count
from django.utils.html import format_html
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'status', 'payment_date', 'tx_ref']
    list_filter = ['status', 'payment_date']
    search_fields = ['user__username', 'user__email', 'tx_ref']
    readonly_fields = ['payment_date']
    ordering = ['-payment_date']
    
    def changelist_view(self, request, extra_context=None):
        # Calculate earnings statistics
        now = timezone.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        
        # Current month earnings
        current_month_payments = Payment.objects.filter(
            status='success',
            payment_date__gte=current_month_start
        )
        current_month_total = current_month_payments.aggregate(Sum('amount'))['amount__sum'] or 0
        current_month_count = current_month_payments.count()
        
        # Last month earnings
        last_month_payments = Payment.objects.filter(
            status='success',
            payment_date__gte=last_month_start,
            payment_date__lt=current_month_start
        )
        last_month_total = last_month_payments.aggregate(Sum('amount'))['amount__sum'] or 0
        last_month_count = last_month_payments.count()
        
        # Total earnings
        total_earnings = Payment.objects.filter(status='success').aggregate(Sum('amount'))['amount__sum'] or 0
        total_payments = Payment.objects.filter(status='success').count()
        
        # Active subscribers (paid in last 30 days)
        thirty_days_ago = now - timedelta(days=30)
        active_subscribers = Payment.objects.filter(
            status='success',
            payment_date__gte=thirty_days_ago
        ).values('user').distinct().count()
        
        extra_context = extra_context or {}
        extra_context.update({
            'earnings_stats': {
                'current_month_total': current_month_total,
                'current_month_count': current_month_count,
                'last_month_total': last_month_total,
                'last_month_count': last_month_count,
                'total_earnings': total_earnings,
                'total_payments': total_payments,
                'active_subscribers': active_subscribers,
                'current_month_name': current_month_start.strftime('%B %Y'),
                'last_month_name': last_month_start.strftime('%B %Y'),
            }
        })
        
        return super().changelist_view(request, extra_context=extra_context)
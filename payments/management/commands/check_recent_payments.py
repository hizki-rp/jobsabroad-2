from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from payments.models import Payment
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Check for recent payments and find users who paid today'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Number of days to look back for payments (default: 1 for today)'
        )

    def handle(self, *args, **options):
        days_back = options['days']
        
        # Calculate the date range
        now = timezone.now()
        start_date = now - timedelta(days=days_back)
        
        self.stdout.write(
            self.style.SUCCESS(f'Checking payments from {start_date.strftime("%Y-%m-%d %H:%M")} to now...')
        )
        
        # Get recent payments
        recent_payments = Payment.objects.filter(
            payment_date__gte=start_date
        ).select_related('user').order_by('-payment_date')
        
        if not recent_payments.exists():
            self.stdout.write(
                self.style.WARNING(f'No payments found in the last {days_back} day(s)')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'Found {recent_payments.count()} payment(s) in the last {days_back} day(s):')
        )
        
        total_amount = 0
        successful_payments = 0
        
        for payment in recent_payments:
            status_color = self.style.SUCCESS if payment.status == 'success' else self.style.ERROR
            
            self.stdout.write(
                f'  • User: {payment.user.username} ({payment.user.email})'
            )
            self.stdout.write(
                f'    Amount: {payment.amount} ETB'
            )
            self.stdout.write(
                status_color(f'    Status: {payment.status}')
            )
            self.stdout.write(
                f'    Date: {payment.payment_date.strftime("%Y-%m-%d %H:%M:%S")}'
            )
            self.stdout.write(
                f'    Reference: {payment.tx_ref}'
            )
            self.stdout.write('')
            
            if payment.status == 'success':
                total_amount += payment.amount
                successful_payments += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Summary:')
        )
        self.stdout.write(f'  Total successful payments: {successful_payments}')
        self.stdout.write(f'  Total amount (successful): {total_amount} ETB')
        
        # Show unique users who paid
        unique_users = recent_payments.values('user__username', 'user__email').distinct()
        self.stdout.write(f'  Unique users who paid: {len(unique_users)}')
        
        for user in unique_users:
            self.stdout.write(f'    - {user["user__username"]} ({user["user__email"]})')
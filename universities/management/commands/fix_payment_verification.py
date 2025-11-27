from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from payments.models import Payment
from universities.models import UserDashboard

class Command(BaseCommand):
    help = 'Fix users who have successful payments but are not verified'

    def handle(self, *args, **options):
        # Find users with successful payments but not verified
        successful_payments = Payment.objects.filter(status='success').values_list('user_id', flat=True).distinct()
        
        fixed_count = 0
        for user_id in successful_payments:
            try:
                user = User.objects.get(id=user_id)
                dashboard, created = UserDashboard.objects.get_or_create(user=user)
                
                if not dashboard.is_verified and dashboard.subscription_status == 'active':
                    dashboard.is_verified = True
                    dashboard.save()
                    fixed_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Fixed verification for user: {user.username}')
                    )
            except User.DoesNotExist:
                continue
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully fixed {fixed_count} users')
        )
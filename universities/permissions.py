from rest_framework.permissions import BasePermission
from django.utils import timezone

class HasActiveSubscription(BasePermission):
    """
    Allows access only to users with an active subscription.
    """
    message = 'You do not have an active subscription or it has expired.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers/staff should always have access for administrative purposes.
        if request.user.is_staff or request.user.is_superuser:
            return True

        try:
            dashboard = request.user.dashboard
            return (dashboard.subscription_status == 'active' and
                    dashboard.subscription_end_date and
                    dashboard.subscription_end_date >= timezone.now().date())
        except AttributeError:
            # This can happen if the dashboard object doesn't exist for some reason.
            return False
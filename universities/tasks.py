from celery import shared_task
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import UserDashboard

@shared_task
def send_welcome_email(user_id):
    """Sends a welcome email to a new user.
    DISABLED: Email sending is currently disabled to improve performance
    """
    # Email sending disabled for now
    return f"Email sending disabled for user_id {user_id}"
    # try:
    #     user = User.objects.get(id=user_id)
    #     subject = 'Welcome to Addis Temari!'
    #     message = f'Hi {user.username},\n\nThank you for registering at Addis Temari. We are excited to have you on board. Explore universities and start planning your future today!\n\nBest regards,\nThe Addis Temari Team'
    #     from_email = 'noreply@addistemari.com'
    #     recipient_list = [user.email]
    #     send_mail(subject, message, from_email, recipient_list)
    #     return f"Welcome email sent to {user.email}"
    # except User.DoesNotExist:
    #     return f"User with id {user_id} does not exist."

@shared_task
def check_subscription_expirations():
    """
    A periodic task to find users whose subscriptions are expiring soon
    and send them a reminder email.
    DISABLED: Email sending is currently disabled to improve performance
    """
    # Email sending disabled for now
    reminder_date = timezone.now().date() + timedelta(days=7)
    expiring_dashboards = UserDashboard.objects.filter(
        subscription_status='active',
        subscription_end_date=reminder_date
    )
    # Email sending code commented out
    # for dashboard in expiring_dashboards:
    #     user = dashboard.user
    #     subject = 'Your Addis Temari Subscription is Expiring Soon'
    #     message = f'Hi {user.username},\n\nYour subscription to Addis Temari is set to expire in 7 days. Please renew your subscription to continue enjoying uninterrupted access to all our features.\n\nBest regards,\nThe Addis Temari Team'
    #     from_email = 'noreply@addistemari.com'
    #     recipient_list = [user.email]
    #     send_mail(subject, message, from_email, recipient_list)
    return f"Email sending disabled. Found {expiring_dashboards.count()} expiring subscriptions."

@shared_task
def send_application_status_update_email(user_id, university_name, new_status):
    """Sends an email to a user when their application status for a university is updated.
    DISABLED: Email sending is currently disabled to improve performance
    """
    # Email sending disabled for now
    return f"Email sending disabled for application status update: user_id={user_id}, university={university_name}, status={new_status}"
    # try:
    #     user = User.objects.get(id=user_id)
    #     
    #     # Make the status more human-readable
    #     formatted_status = new_status.replace('_', ' ').title()
    #
    #     subject = f'Application Status Update for {university_name}'
    #     message = f'Hi {user.username},\n\nYour application status for {university_name} has been updated to: "{formatted_status}".\n\nYou can view your updated dashboard here: https://addistemari.com/dashboard\n\nBest of luck!\nThe Addis Temari Team'
    #     from_email = 'noreply@addistemari.com'
    #     recipient_list = [user.email]
    #     send_mail(subject, message, from_email, recipient_list)
    #     return f"Application status update email sent to {user.email} for {university_name}."
    # except User.DoesNotExist:
    #     return f"User with id {user_id} does not exist."
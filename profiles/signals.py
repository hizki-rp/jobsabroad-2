from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def send_welcome_email_on_registration(sender, instance, created, **kwargs):
    """
    Send welcome email to new users upon registration
    """
    if created:
        try:
            # Get user's first name or username for personalization
            user_name = instance.first_name if instance.first_name else instance.username
            
            # Welcome message for new users
            subject = "Welcome to Addis Temari - Complete Your Account Setup"
            message = f"""Dear {user_name},

Welcome to Addis Temari! We're excited to have you join our community of ambitious students pursuing their dreams of studying abroad.

Thank you for creating your account! To get the most out of your Addis Temari experience, you must complete your account by subscribing to our premium services. This will unlock:

🎓 Access to our comprehensive university database
📋 Personalized application guidance  
💼 Scholarship opportunities
📊 Application tracking tools
🎯 Expert support throughout your journey

Complete your account activation today and take the first step towards your international education goals!

Best regards,
The Addis Temari Team"""

            # Send email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.email],
                fail_silently=False,
            )
            
            logger.info(f"Welcome email sent to {instance.email}")
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {instance.email}: {str(e)}")

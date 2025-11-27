# h:\Django2\UNI-FINDER-GIT\backend\profiles\models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True)
    dob = models.DateField(null=True, blank=True)
    current_role = models.CharField(max_length=100, blank=True)
    years_experience = models.PositiveIntegerField(null=True, blank=True)
    skills = models.JSONField(default=list, blank=True)
    country = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f'{self.user.username} Profile'

class WorkExperience(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='work_experiences')
    company_name = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.job_title} at {self.company_name}"

class JobPreference(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='job_preference')
    desired_start_date = models.DateField(null=True, blank=True)
    work_permit_status = models.CharField(max_length=100, blank=True)
    desired_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Job preferences for {self.profile.user.username}"

# These signals automatically create a Profile when a new User is created.
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        profile, _ = Profile.objects.get_or_create(user=instance)
        JobPreference.objects.get_or_create(profile=profile)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        # This will also trigger the creation of JobPreference via the signal
        Profile.objects.create(user=instance) 

# This signal seems to be duplicated in profiles/signals.py. I'll remove it from here.
@receiver(post_save, sender=User)
def send_welcome_email_on_registration(sender, instance, created, **kwargs):
    """
    Send welcome email to new users upon registration
    DISABLED: Email sending is currently disabled to improve performance
    """
    # Email sending disabled for now
    if created:
        logger.info(f"User {instance.username} registered - email sending disabled")
        # Email sending code commented out for performance
        # try:
        #     # Get user's first name or username for personalization
        #     user_name = instance.first_name if instance.first_name else instance.username
        #     
        #     # Welcome message for new users
        #     subject = "Welcome to Addis Temari - Complete Your Account Setup"
        #     message = f"""Dear {user_name},
        #
        # Welcome to Addis Temari! We're excited to have you join our community of ambitious students pursuing their dreams of studying abroad.
        #
        # Thank you for creating your account! To get the most out of your Addis Temari experience, you must complete your account by subscribing to our premium services. This will unlock:
        #
        # 🎓 Access to our comprehensive university database
        # 📋 Personalized application guidance  
        # 💼 Scholarship opportunities
        # 📊 Application tracking tools
        # 🎯 Expert support throughout your journey
        #
        # Complete your account activation today and take the first step towards your international education goals!
        #
        # Best regards,
        # The Addis Temari Team"""
        #
        #     # Send email
        #     send_mail(
        #         subject=subject,
        #         message=message,
        #         from_email=settings.DEFAULT_FROM_EMAIL,
        #         recipient_list=[instance.email],
        #         fail_silently=False,
        #     )
        #     
        #     logger.info(f"Welcome email sent to {instance.email}")
        #     
        # except Exception as e:
        #     logger.error(f"Failed to send welcome email to {instance.email}: {str(e)}")

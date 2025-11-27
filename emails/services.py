from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from .models import EmailLog, EmailTemplate
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service class for handling email operations"""
    
    @staticmethod
    def send_single_email(recipient, subject, body, template=None, sent_by=None):
        """
        Send a single email and log it
        """
        try:
            # Create email log entry
            email_log = EmailLog.objects.create(
                recipient=recipient,
                subject=subject,
                body=body,
                template=template,
                sent_by=sent_by,
                status='pending'
            )
            
            # Send email with detailed error handling
            try:
                result = send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient.email],
                    fail_silently=False,
                )
                
                if result:
                    # Update log on success
                    email_log.status = 'sent'
                    email_log.sent_at = timezone.now()
                    email_log.save()
                    
                    logger.info(f"Email sent successfully to {recipient.email}")
                    return True, "Email sent successfully"
                else:
                    # Update log on failure
                    email_log.status = 'failed'
                    email_log.error_message = "Email sending returned False"
                    email_log.save()
                    
                    logger.error(f"Email sending returned False for {recipient.email}")
                    return False, "Email sending failed - no error details"
                    
            except Exception as email_error:
                # Update log on failure
                email_log.status = 'failed'
                email_log.error_message = str(email_error)
                email_log.save()
                
                logger.error(f"SMTP error sending email to {recipient.email}: {str(email_error)}")
                return False, f"SMTP Error: {str(email_error)}"
            
        except Exception as e:
            # Update log on failure
            if 'email_log' in locals():
                email_log.status = 'failed'
                email_log.error_message = str(e)
                email_log.save()
            
            logger.error(f"Failed to send email to {recipient.email}: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def send_bulk_email(recipients, subject, body, template=None, sent_by=None):
        """
        Send bulk emails and log each one
        """
        results = {
            'sent': 0,
            'failed': 0,
            'errors': []
        }
        
        for recipient in recipients:
            success, message = EmailService.send_single_email(
                recipient, subject, body, template, sent_by
            )
            
            if success:
                results['sent'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(f"{recipient.email}: {message}")
        
        return results
    
    @staticmethod
    def send_template_email(recipient, template_name, context=None, sent_by=None):
        """
        Send email using a template
        """
        try:
            template = EmailTemplate.objects.get(name=template_name, is_active=True)
            
            # Prepare context
            if context is None:
                context = {}
            
            # Add user information to context
            context.update({
                'user_name': recipient.first_name or recipient.username,
                'user_email': recipient.email,
                'user_username': recipient.username,
            })
            
            # Render subject and body with context
            subject = template.subject.format(**context)
            body = template.body.format(**context)
            
            return EmailService.send_single_email(
                recipient, subject, body, template, sent_by
            )
            
        except EmailTemplate.DoesNotExist:
            return False, f"Template '{template_name}' not found"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def get_user_emails(user_ids=None, active_only=True):
        """
        Get users for email sending
        """
        queryset = User.objects.all()
        
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        if user_ids:
            queryset = queryset.filter(id__in=user_ids)
        
        return queryset.select_related('profile')
    
    @staticmethod
    def create_default_templates():
        """
        Create default email templates
        """
        templates = [
            {
                'name': 'welcome',
                'subject': 'Welcome to Addis Temari!',
                'body': '''Dear {{user_name}},

Welcome to Addis Temari! We're excited to have you join our community of students pursuing their dreams.

Your account has been successfully created and you can now:
- Browse our extensive database of universities
- Track your application progress
- Access premium content and features

If you have any questions, feel free to contact our support team.

Best regards,
The Addis Temari Team'''
            },
            {
                'name': 'subscription_reminder',
                'subject': 'Your Addis Temari subscription is expiring soon',
                'body': '''Dear {{user_name}},

Your Addis Temari subscription will expire soon. To continue enjoying our premium features, please renew your subscription.

Premium features include:
- Access to detailed university information
- Application tracking tools
- Priority support

Renew now to avoid any interruption in service.

Best regards,
The Addis Temari Team'''
            },
            {
                'name': 'application_deadline',
                'subject': 'Important: Application deadline approaching',
                'body': '''Dear {{user_name}},

This is a friendly reminder that you have university applications with upcoming deadlines.

Please check your dashboard to review your applications and ensure all required documents are submitted on time.

Best regards,
The Addis Temari Team'''
            }
        ]
        
        for template_data in templates:
            EmailTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults=template_data
            )




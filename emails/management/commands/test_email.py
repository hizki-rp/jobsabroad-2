from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Test email configuration by sending a test email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            default='addistemari.m@gmail.com',
            help='Email address to send test email to'
        )

    def handle(self, *args, **options):
        recipient = options['to']
        
        self.stdout.write('Testing email configuration...')
        self.stdout.write(f'EMAIL_BACKEND: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'EMAIL_HOST: {settings.EMAIL_HOST}')
        self.stdout.write(f'EMAIL_PORT: {settings.EMAIL_PORT}')
        self.stdout.write(f'EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write('')
        
        try:
            subject = 'Test Email from Addis Temari System'
            message = '''
Hello!

This is a test email from the Addis Temari system.

If you receive this email, the email configuration is working correctly!

Email Configuration Details:
- Backend: SMTP
- Host: Gmail SMTP
- TLS: Enabled
- From: addistemari.m@gmail.com

Best regards,
Addis Temari Team
            '''
            
            self.stdout.write(f'Sending test email to: {recipient}')
            
            result = send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            
            if result:
                self.stdout.write(
                    self.style.SUCCESS('✅ Email sent successfully!')
                )
                self.stdout.write('Check your inbox for the test email.')
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Email sending failed')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error sending email: {str(e)}')
            )
            self.stdout.write('\nTroubleshooting tips:')
            self.stdout.write('1. Make sure the Gmail app password is correct')
            self.stdout.write('2. Ensure 2-factor authentication is enabled on the Gmail account')
            self.stdout.write('3. Check that the Gmail account is not locked or restricted')
            self.stdout.write('4. Verify the app password was generated correctly')


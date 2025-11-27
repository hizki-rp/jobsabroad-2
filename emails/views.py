from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.db.models import Q
from .models import EmailTemplate, EmailLog, BulkEmail
from .serializers import (
    EmailTemplateSerializer, EmailLogSerializer, BulkEmailSerializer, UserEmailSerializer
)
from .services import EmailService
from django.utils import timezone


class EmailTemplateListCreateView(generics.ListCreateAPIView):
    """List and create email templates"""
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]


class EmailTemplateRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete email templates"""
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]


class EmailLogListView(generics.ListAPIView):
    """List email logs with filtering"""
    serializer_class = EmailLogSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        queryset = EmailLog.objects.select_related('recipient', 'template', 'sent_by')
        
        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by recipient
        recipient = self.request.query_params.get('recipient')
        if recipient:
            queryset = queryset.filter(recipient__username__icontains=recipient)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        return queryset.order_by('-created_at')


class BulkEmailListCreateView(generics.ListCreateAPIView):
    """List and create bulk emails"""
    serializer_class = BulkEmailSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        return BulkEmail.objects.select_related('template', 'created_by').order_by('-created_at')


class UserEmailListView(generics.ListAPIView):
    """List users for email selection"""
    serializer_class = UserEmailSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        queryset = User.objects.filter(is_active=True)
        
        # Search by username or email
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        return queryset.order_by('username')


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def send_single_email(request):
    """Send email to a single user"""
    try:
        user_id = request.data.get('user_id')
        subject = request.data.get('subject')
        body = request.data.get('body')
        template_id = request.data.get('template_id')
        
        if not all([user_id, subject, body]):
            return Response(
                {'error': 'user_id, subject, and body are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        template = None
        if template_id:
            try:
                template = EmailTemplate.objects.get(id=template_id)
            except EmailTemplate.DoesNotExist:
                return Response(
                    {'error': 'Template not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        success, message = EmailService.send_single_email(
            user, subject, body, template, request.user
        )
        
        if success:
            return Response({'message': 'Email sent successfully'})
        else:
            return Response(
                {'error': message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def send_bulk_email(request):
    """Send email to multiple users"""
    try:
        user_ids = request.data.get('user_ids', [])
        subject = request.data.get('subject')
        body = request.data.get('body')
        template_id = request.data.get('template_id')
        
        if not all([user_ids, subject, body]):
            return Response(
                {'error': 'user_ids, subject, and body are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        users = User.objects.filter(id__in=user_ids, is_active=True)
        if not users.exists():
            return Response(
                {'error': 'No active users found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        template = None
        if template_id:
            try:
                template = EmailTemplate.objects.get(id=template_id)
            except EmailTemplate.DoesNotExist:
                return Response(
                    {'error': 'Template not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Create bulk email record
        bulk_email = BulkEmail.objects.create(
            name=f"Bulk Email - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            subject=subject,
            body=body,
            template=template,
            total_recipients=len(user_ids),
            created_by=request.user
        )
        bulk_email.recipients.set(users)
        
        # Send emails
        results = EmailService.send_bulk_email(
            users, subject, body, template, request.user
        )
        
        # Update bulk email record
        bulk_email.sent_count = results['sent']
        bulk_email.failed_count = results['failed']
        bulk_email.status = 'sent' if results['failed'] == 0 else 'failed'
        bulk_email.sent_at = timezone.now()
        bulk_email.save()
        
        return Response({
            'message': f'Bulk email sent. {results["sent"]} sent, {results["failed"]} failed',
            'results': results,
            'bulk_email_id': bulk_email.id
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def send_template_email(request):
    """Send email using a template"""
    try:
        user_id = request.data.get('user_id')
        template_name = request.data.get('template_name')
        context = request.data.get('context', {})
        
        if not all([user_id, template_name]):
            return Response(
                {'error': 'user_id and template_name are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        success, message = EmailService.send_template_email(
            user, template_name, context, request.user
        )
        
        if success:
            return Response({'message': 'Template email sent successfully'})
        else:
            return Response(
                {'error': message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def email_statistics(request):
    """Get email statistics"""
    try:
        total_emails = EmailLog.objects.count()
        sent_emails = EmailLog.objects.filter(status='sent').count()
        failed_emails = EmailLog.objects.filter(status='failed').count()
        pending_emails = EmailLog.objects.filter(status='pending').count()
        
        # Recent activity (last 7 days)
        from datetime import timedelta
        week_ago = timezone.now() - timedelta(days=7)
        recent_emails = EmailLog.objects.filter(created_at__gte=week_ago).count()
        
        return Response({
            'total_emails': total_emails,
            'sent_emails': sent_emails,
            'failed_emails': failed_emails,
            'pending_emails': pending_emails,
            'recent_emails': recent_emails,
            'success_rate': (sent_emails / total_emails * 100) if total_emails > 0 else 0
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def test_email_config(request):
    """Test email configuration"""
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        # Get test email address from request or use default
        test_email = request.data.get('email', 'addistemari.m@gmail.com')
        
        # Send test email
        subject = 'Test Email from Addis Temari System'
        message = '''
Hello!

This is a test email from the Addis Temari system to verify email configuration.

Email Configuration:
- Backend: SMTP
- Host: Gmail SMTP
- TLS: Enabled
- From: addistemari.m@gmail.com

If you receive this email, the email configuration is working correctly!

Best regards,
Addis Temari Team
        '''
        
        result = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[test_email],
            fail_silently=False,
        )
        
        if result:
            return Response({
                'message': f'Test email sent successfully to {test_email}',
                'status': 'success'
            })
        else:
            return Response({
                'error': 'Email sending returned False',
                'status': 'failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        return Response({
            'error': f'Email test failed: {str(e)}',
            'status': 'failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




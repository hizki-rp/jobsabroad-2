from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import CreatorApplicationSettings, CreatorApplication, CreatorProfile
from .serializers import (
    CreatorApplicationSettingsSerializer, CreatorApplicationSerializer,
    CreatorApplicationCreateSerializer
)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def creator_application_status(request):
    """Check if creator applications are open and user's application status"""
    settings = CreatorApplicationSettings.objects.first()
    if not settings:
        settings = CreatorApplicationSettings.objects.create()
    
    user_application = None
    try:
        user_application = CreatorApplication.objects.get(user=request.user)
    except CreatorApplication.DoesNotExist:
        pass
    
    data = {
        'applications_open': settings.applications_open,
        'application_deadline': settings.application_deadline,
        'requirements': settings.requirements,
        'user_application': CreatorApplicationSerializer(user_application).data if user_application else None,
        'can_apply': settings.applications_open and not user_application
    }
    
    return Response(data)

class CreatorApplicationCreateView(generics.CreateAPIView):
    """Submit creator application"""
    serializer_class = CreatorApplicationCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        # Check if applications are open
        settings = CreatorApplicationSettings.objects.first()
        if not settings or not settings.applications_open:
            return Response(
                {'error': 'Creator applications are currently closed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user already applied
        if CreatorApplication.objects.filter(user=request.user).exists():
            return Response(
                {'error': 'You have already submitted an application'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().create(request, *args, **kwargs)

# Admin views
class AdminCreatorApplicationSettingsView(generics.RetrieveUpdateAPIView):
    """Admin: Manage creator application settings"""
    serializer_class = CreatorApplicationSettingsSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_object(self):
        settings, created = CreatorApplicationSettings.objects.get_or_create()
        return settings

class AdminCreatorApplicationListView(generics.ListAPIView):
    """Admin: List all creator applications"""
    serializer_class = CreatorApplicationSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        queryset = CreatorApplication.objects.all()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def admin_review_application(request, application_id):
    """Admin: Approve or reject creator application"""
    application = get_object_or_404(CreatorApplication, id=application_id)
    action = request.data.get('action')  # 'approve' or 'reject'
    admin_notes = request.data.get('admin_notes', '')
    
    if action == 'approve':
        application.status = 'approved'
        # Create or update creator profile
        creator_profile, created = CreatorProfile.objects.get_or_create(
            user=application.user,
            defaults={
                'expertise_areas': application.expertise_areas,
                'is_approved_creator': True
            }
        )
        if not created:
            creator_profile.is_approved_creator = True
            creator_profile.save()
            
    elif action == 'reject':
        application.status = 'rejected'
    else:
        return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
    
    application.admin_notes = admin_notes
    application.reviewed_at = timezone.now()
    application.reviewed_by = request.user
    application.save()
    
    return Response({
        'message': f'Application {action}d successfully',
        'application': CreatorApplicationSerializer(application).data
    })
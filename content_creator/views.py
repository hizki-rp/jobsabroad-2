from rest_framework import generics, status, permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import models
from .models import CreatorApplication, OpportunityPost, CreatorRevenue, ApplicationSettings
from .serializers import CreatorApplicationSerializer, OpportunityPostSerializer, ApplicationSettingsSerializer
from universities.permissions import HasActiveSubscription
from decimal import Decimal

class ApplicationSettingsView(generics.RetrieveAPIView):
    serializer_class = ApplicationSettingsSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_object(self):
        return ApplicationSettings.get_settings()

class CreateCreatorApplicationView(generics.CreateAPIView):
    serializer_class = CreatorApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        # Check if applications are open
        settings = ApplicationSettings.get_settings()
        if not settings.is_open:
            raise serializers.ValidationError("Creator applications are currently closed.")
        
        # Check if user already has an application
        if CreatorApplication.objects.filter(user=self.request.user).exists():
            raise serializers.ValidationError("You have already submitted an application.")
        
        serializer.save(user=self.request.user)

class OpportunityPostListView(generics.ListAPIView):
    serializer_class = OpportunityPostSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = OpportunityPost.objects.filter(is_active=True, is_draft=False)
        
        # Get query parameters
        content_type = self.request.query_params.get('type', None)
        search = self.request.query_params.get('search', None)
        
        # Filter by content type
        if content_type:
            queryset = queryset.filter(content_type=content_type)
        
        # Search in title and description
        if search:
            queryset = queryset.filter(
                models.Q(title__icontains=search) | 
                models.Q(description__icontains=search)
            )
        
        return queryset.order_by('-created_at')

class CreateOpportunityPostView(generics.CreateAPIView):
    serializer_class = OpportunityPostSerializer
    permission_classes = [permissions.AllowAny]  # Temporarily allow any for testing
    
    def perform_create(self, serializer):
        # For testing, use a default user if not authenticated
        from django.contrib.auth.models import User
        creator = self.request.user if self.request.user.is_authenticated else User.objects.first()
        print(f"Request data: {self.request.data}")
        print(f"Serializer is valid: {serializer.is_valid()}")
        if not serializer.is_valid():
            print(f"Serializer errors: {serializer.errors}")
        serializer.save(creator=creator)

class OpportunityPostDetailView(generics.RetrieveAPIView):
    serializer_class = OpportunityPostSerializer
    permission_classes = [permissions.AllowAny]
    queryset = OpportunityPost.objects.all()

class UpdateOpportunityPostView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OpportunityPostSerializer
    permission_classes = [permissions.AllowAny]
    queryset = OpportunityPost.objects.all()
    
    def perform_update(self, serializer):
        serializer.save()
    
    def perform_destroy(self, instance):
        instance.delete()

class DraftPostListView(generics.ListAPIView):
    serializer_class = OpportunityPostSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        # Show drafts for current user or all drafts for testing
        return OpportunityPost.objects.filter(is_draft=True)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def subscribe_to_creator_post(request, post_id):
    """Handle subscription through creator post with revenue sharing"""
    post = get_object_or_404(OpportunityPost, id=post_id, is_active=True)
    user = request.user
    
    # Check if user already has active subscription
    dashboard = getattr(user, 'dashboard', None)
    if dashboard and dashboard.subscription_status == 'active':
        return Response({'message': 'You already have an active subscription'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # Initialize payment (similar to existing subscription logic)
    # This would integrate with your existing Chapa payment system
    # For now, we'll create a placeholder response
    
    return Response({
        'message': 'Payment initialization would happen here',
        'post_title': post.title,
        'creator': post.creator.username,
        'checkout_url': 'https://checkout.chapa.co/placeholder'  # This would be real Chapa URL
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def creator_dashboard(request):
    """Get creator's posts and revenue stats"""
    # Allow admins or approved creators
    if not (request.user.is_staff or 
            CreatorApplication.objects.filter(user=request.user, status='approved').exists()):
        return Response({'error': 'Not an approved creator'}, status=status.HTTP_403_FORBIDDEN)
    
    posts = OpportunityPost.objects.filter(creator=request.user)
    revenues = CreatorRevenue.objects.filter(creator=request.user)
    
    total_earnings = sum(revenue.amount for revenue in revenues)
    
    return Response({
        'posts_count': posts.count(),
        'total_earnings': total_earnings,
        'recent_posts': OpportunityPostSerializer(posts[:5], many=True).data
    })
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import F
from django.utils import timezone
from universities.permissions import HasActiveSubscription
from .models import CreatorProfile, Opportunity, SubscriptionAttribution, OpportunityView
from .serializers import (
    CreatorProfileSerializer, OpportunityListSerializer, 
    OpportunityDetailSerializer, OpportunityCreateSerializer,
    SubscriptionAttributionSerializer, CreatorEarningSerializer
)

class OpportunityListView(generics.ListAPIView):
    """List all published opportunities (preview mode for all users)"""
    serializer_class = OpportunityListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = Opportunity.objects.filter(status='published')
        
        # Filter by content type
        content_type = self.request.query_params.get('type')
        if content_type:
            queryset = queryset.filter(content_type=content_type)
        
        # Filter by country
        country = self.request.query_params.get('country')
        if country:
            queryset = queryset.filter(country__icontains=country)
        
        # Filter by tags
        tags = self.request.query_params.get('tags')
        if tags:
            tag_list = tags.split(',')
            queryset = queryset.filter(tags__overlap=tag_list)
        
        return queryset.select_related('creator', 'creator__creator_profile')

class OpportunityDetailView(generics.RetrieveAPIView):
    """Get opportunity details (full content for premium users only)"""
    queryset = Opportunity.objects.filter(status='published')
    permission_classes = [permissions.AllowAny]
    
    def get_serializer_class(self):
        # Check if user has active subscription
        user = self.request.user
        has_subscription = (user.is_authenticated and 
                          hasattr(user, 'dashboard') and 
                          user.dashboard.subscription_status == 'active')
        
        if has_subscription:
            return OpportunityDetailSerializer
        else:
            return OpportunityListSerializer
    
    def retrieve(self, request, *args, **kwargs):
        opportunity = self.get_object()
        
        # Track view
        self._track_view(opportunity, request)
        
        # Increment view count
        Opportunity.objects.filter(id=opportunity.id).update(views_count=F('views_count') + 1)
        
        serializer = self.get_serializer(opportunity)
        data = serializer.data
        
        # Add subscription status info
        has_subscription = (request.user.is_authenticated and 
                          hasattr(request.user, 'dashboard') and 
                          request.user.dashboard.subscription_status == 'active')
        data['user_has_subscription'] = has_subscription
        data['subscription_required'] = not has_subscription
        
        return Response(data)
    
    def _track_view(self, opportunity, request):
        """Track opportunity view for analytics"""
        ip_address = self._get_client_ip(request)
        OpportunityView.objects.get_or_create(
            opportunity=opportunity,
            user=request.user if request.user.is_authenticated else None,
            ip_address=ip_address
        )
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class OpportunityCreateView(generics.CreateAPIView):
    """Create new opportunity (creators only)"""
    serializer_class = OpportunityCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        # Create or get creator profile
        creator_profile, created = CreatorProfile.objects.get_or_create(
            user=self.request.user
        )
        serializer.save()

class MyOpportunitiesView(generics.ListAPIView):
    """List user's own opportunities"""
    serializer_class = OpportunityDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Opportunity.objects.filter(creator=self.request.user)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def subscribe_from_opportunity(request, opportunity_id):
    """Subscribe to premium and attribute to creator"""
    opportunity = get_object_or_404(Opportunity, id=opportunity_id, status='published')
    user = request.user
    
    # Check if user already has active subscription
    if hasattr(user, 'dashboard') and user.dashboard.subscription_status == 'active':
        return Response({'error': 'User already has active subscription'}, status=status.HTTP_400_BAD_REQUEST)
    
    # This would integrate with your existing Chapa payment system
    # For now, we'll create the attribution record
    attribution, created = SubscriptionAttribution.objects.get_or_create(
        user=user,
        creator=opportunity.creator,
        defaults={
            'opportunity': opportunity,
            'subscription_start': timezone.now(),
            'is_active': True
        }
    )
    
    if created:
        # Increment subscribers gained for this opportunity
        Opportunity.objects.filter(id=opportunity_id).update(
            subscribers_gained=F('subscribers_gained') + 1
        )
        
        # Update creator's active subscribers count
        CreatorProfile.objects.filter(user=opportunity.creator).update(
            active_subscribers=F('active_subscribers') + 1
        )
    
    return Response({
        'message': 'Subscription attribution created',
        'creator': opportunity.creator.username,
        'opportunity': opportunity.title
    })

class AdminOpportunityListView(generics.ListAPIView):
    """Admin view to list all opportunities with filtering"""
    serializer_class = OpportunityDetailSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        queryset = Opportunity.objects.all().select_related('creator')
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by content type
        content_type = self.request.query_params.get('type')
        if content_type:
            queryset = queryset.filter(content_type=content_type)
        
        return queryset.order_by('-created_at')

@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def admin_approve_opportunity(request, opportunity_id):
    """Admin endpoint to approve/reject opportunities"""
    opportunity = get_object_or_404(Opportunity, id=opportunity_id)
    action = request.data.get('action')  # 'approve' or 'reject'
    
    if action == 'approve':
        opportunity.status = 'published'
    elif action == 'reject':
        opportunity.status = 'rejected'
    else:
        return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
    
    opportunity.save()
    
    return Response({
        'message': f'Opportunity {action}d successfully',
        'opportunity': OpportunityDetailSerializer(opportunity).data
    })

class CreatorDashboardView(generics.RetrieveAPIView):
    """Creator dashboard with earnings and stats"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get or create creator profile
        creator_profile, created = CreatorProfile.objects.get_or_create(user=user)
        
        # Get opportunities stats
        opportunities = Opportunity.objects.filter(creator=user)
        total_opportunities = opportunities.count()
        published_opportunities = opportunities.filter(status='published').count()
        total_views = sum(opp.views_count for opp in opportunities)
        total_subscribers_gained = sum(opp.subscribers_gained for opp in opportunities)
        
        # Get recent earnings
        recent_earnings = user.earnings.all()[:6]
        
        data = {
            'creator_profile': CreatorProfileSerializer(creator_profile).data,
            'stats': {
                'total_opportunities': total_opportunities,
                'published_opportunities': published_opportunities,
                'total_views': total_views,
                'total_subscribers_gained': total_subscribers_gained,
                'active_subscribers': creator_profile.active_subscribers,
                'total_earnings': creator_profile.total_earnings
            },
            'recent_earnings': CreatorEarningSerializer(recent_earnings, many=True).data,
            'recent_opportunities': OpportunityDetailSerializer(
                opportunities[:5], many=True
            ).data
        }
        
        return Response(data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def opportunity_stats(request, opportunity_id):
    """Get detailed stats for a specific opportunity"""
    from django.db import models as django_models
    
    opportunity = get_object_or_404(
        Opportunity, 
        id=opportunity_id, 
        creator=request.user
    )
    
    # Get view analytics
    views_by_day = opportunity.views.extra(
        select={'day': 'date(viewed_at)'}
    ).values('day').annotate(count=django_models.Count('id')).order_by('day')
    
    data = {
        'opportunity': OpportunityDetailSerializer(opportunity).data,
        'total_views': opportunity.views_count,
        'unique_viewers': opportunity.views.values('user').distinct().count(),
        'subscribers_gained': opportunity.subscribers_gained,
        'views_by_day': list(views_by_day)
    }
    
    return Response(data)
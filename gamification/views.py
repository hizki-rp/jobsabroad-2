from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from .models import Achievement, UserProfile, Leaderboard
from .serializers import UserProfileSerializer, LeaderboardSerializer, AchievementSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    serializer = UserProfileSerializer(profile)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def leaderboard(request):
    period = request.GET.get('period', 'all_time')
    leaderboard_data = Leaderboard.objects.filter(period=period).order_by('rank')[:10]
    serializer = LeaderboardSerializer(leaderboard_data, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_achievements(request):
    achievements = Achievement.objects.filter(is_active=True)
    serializer = AchievementSerializer(achievements, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_achievements(request):
    """Manually trigger achievement check for current user"""
    from .signals import award_achievement
    from universities.models import UserDashboard
    
    user = request.user
    awarded = []
    
    try:
        dashboard = UserDashboard.objects.get(user=user)
        
        # Check all achievements
        if award_achievement(user, 'first_login'):
            awarded.append('first_login')
        
        if user.first_name and user.last_name and user.email:
            if award_achievement(user, 'profile_complete'):
                awarded.append('profile_complete')
        
        if dashboard.favorites.count() >= 5:
            if award_achievement(user, 'favorite_collector'):
                awarded.append('favorite_collector')
        
        return Response({
            'message': f'Checked achievements for {user.username}',
            'newly_awarded': awarded
        })
        
    except UserDashboard.DoesNotExist:
        return Response({'error': 'User dashboard not found'}, status=400)
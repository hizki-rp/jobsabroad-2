from rest_framework import serializers
from .models import Achievement, UserAchievement, UserProfile, Leaderboard

class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = ['id', 'name', 'description', 'category', 'icon', 'points']

class UserAchievementSerializer(serializers.ModelSerializer):
    achievement = AchievementSerializer(read_only=True)
    
    class Meta:
        model = UserAchievement
        fields = ['achievement', 'earned_at']

class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    achievements = UserAchievementSerializer(source='user.achievements', many=True, read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['username', 'total_points', 'level', 'streak_days', 'achievements']

class LeaderboardSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Leaderboard
        fields = ['username', 'points', 'rank', 'period']
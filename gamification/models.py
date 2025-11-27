from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Achievement(models.Model):
    CATEGORY_CHOICES = [
        ('profile', 'Profile'),
        ('university', 'University'),
        ('application', 'Application'),
        ('social', 'Social'),
        ('milestone', 'Milestone'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    icon = models.CharField(max_length=50, default='🏆')
    points = models.IntegerField(default=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'achievement')
    
    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='game_profile')
    total_points = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    streak_days = models.IntegerField(default=0)
    last_activity = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.username} - Level {self.level}"
    
    def add_points(self, points):
        self.total_points += points
        self.level = (self.total_points // 100) + 1
        self.save()

class Leaderboard(models.Model):
    PERIOD_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('all_time', 'All Time'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    points = models.IntegerField()
    rank = models.IntegerField()
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    class Meta:
        unique_together = ('user', 'period', 'period_start')
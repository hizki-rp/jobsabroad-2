from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.user_profile, name='user_profile'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('achievements/', views.available_achievements, name='available_achievements'),
    path('check-achievements/', views.check_achievements, name='check_achievements'),
]
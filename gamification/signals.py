from django.db.models.signals import post_save, m2m_changed
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.contrib.auth.models import User
from universities.models import UserDashboard
from .models import Achievement, UserAchievement, UserProfile

@receiver(post_save, sender=User)
def create_user_game_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(user_logged_in)
def check_login_achievements(sender, user, request, **kwargs):
    # Award first login achievement
    award_achievement(user, 'first_login')
    
    # Update user activity for streak tracking
    profile, _ = UserProfile.objects.get_or_create(user=user)
    from django.utils import timezone
    profile.last_activity = timezone.now()
    profile.save()

@receiver(post_save, sender=User)
def check_profile_achievements(sender, instance, **kwargs):
    # Profile completion achievement
    if instance.first_name and instance.last_name and instance.email:
        award_achievement(instance, 'profile_complete')

@receiver(post_save, sender=UserDashboard)
def check_subscription_achievements(sender, instance, **kwargs):
    # Skip achievement checks during dashboard saves to improve performance
    pass

@receiver(m2m_changed, sender=UserDashboard.favorites.through)
def check_favorites_achievements(sender, instance, action, **kwargs):
    if action == 'post_add':
        # Use cached count to avoid extra query
        try:
            if instance.favorites.count() >= 5:
                award_achievement(instance.user, 'favorite_collector')
        except Exception:
            pass  # Skip if error to avoid breaking dashboard

@receiver(m2m_changed, sender=UserDashboard.applied.through)
def check_application_achievements(sender, instance, action, **kwargs):
    if action == 'post_add':
        applied_count = instance.applied.count()
        if applied_count >= 1:
            award_achievement(instance.user, 'first_application')
        if applied_count >= 10:
            award_achievement(instance.user, 'application_master')

@receiver(m2m_changed, sender=UserDashboard.accepted.through)
def check_acceptance_achievements(sender, instance, action, **kwargs):
    if action == 'post_add':
        if instance.accepted.count() >= 1:
            award_achievement(instance.user, 'first_acceptance')

@receiver(m2m_changed, sender=UserDashboard.visa_approved.through)
def check_visa_achievements(sender, instance, action, **kwargs):
    if action == 'post_add':
        if instance.visa_approved.count() >= 1:
            award_achievement(instance.user, 'visa_ready')

def award_achievement(user, achievement_name):
    try:
        achievement = Achievement.objects.get(name=achievement_name)
        user_achievement, created = UserAchievement.objects.get_or_create(
            user=user, 
            achievement=achievement
        )
        if created:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.add_points(achievement.points)
            print(f"🎉 Achievement unlocked: {user.username} earned '{achievement.name}' (+{achievement.points} points)")
    except Exception as e:
        print(f"Error awarding achievement {achievement_name}: {e}")
        pass
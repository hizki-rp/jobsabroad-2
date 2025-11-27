from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from universities.models import UserDashboard
from gamification.models import Achievement, UserAchievement, UserProfile

class Command(BaseCommand):
    help = 'Award achievements to existing users based on their current data'

    def handle(self, *args, **options):
        users_updated = 0
        achievements_awarded = 0

        for user in User.objects.all():
            try:
                dashboard = UserDashboard.objects.get(user=user)
                profile, created = UserProfile.objects.get_or_create(user=user)
                
                # Check and award achievements
                awarded_this_user = []
                
                # First login (for users with active subscriptions)
                if dashboard.subscription_status == 'active':
                    if self.award_achievement(user, 'first_login'):
                        awarded_this_user.append('first_login')
                
                # Profile completion
                if user.first_name and user.last_name and user.email:
                    if self.award_achievement(user, 'profile_complete'):
                        awarded_this_user.append('profile_complete')
                
                # Favorite collector (5+ favorites)
                if dashboard.favorites.count() >= 5:
                    if self.award_achievement(user, 'favorite_collector'):
                        awarded_this_user.append('favorite_collector')
                
                # First application
                if dashboard.applied.count() >= 1:
                    if self.award_achievement(user, 'first_application'):
                        awarded_this_user.append('first_application')
                
                # Application master (10+ applications)
                if dashboard.applied.count() >= 10:
                    if self.award_achievement(user, 'application_master'):
                        awarded_this_user.append('application_master')
                
                # First acceptance
                if dashboard.accepted.count() >= 1:
                    if self.award_achievement(user, 'first_acceptance'):
                        awarded_this_user.append('first_acceptance')
                
                # Visa ready
                if dashboard.visa_approved.count() >= 1:
                    if self.award_achievement(user, 'visa_ready'):
                        awarded_this_user.append('visa_ready')
                
                if awarded_this_user:
                    users_updated += 1
                    achievements_awarded += len(awarded_this_user)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'User {user.username}: awarded {", ".join(awarded_this_user)}'
                        )
                    )
                
            except UserDashboard.DoesNotExist:
                continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Updated {users_updated} users with {achievements_awarded} total achievements'
            )
        )

    def award_achievement(self, user, achievement_name):
        try:
            achievement = Achievement.objects.get(name=achievement_name)
            user_achievement, created = UserAchievement.objects.get_or_create(
                user=user, 
                achievement=achievement
            )
            if created:
                profile, _ = UserProfile.objects.get_or_create(user=user)
                profile.add_points(achievement.points)
                return True
        except Achievement.DoesNotExist:
            pass
        return False
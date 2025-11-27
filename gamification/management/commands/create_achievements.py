from django.core.management.base import BaseCommand
from gamification.models import Achievement

class Command(BaseCommand):
    help = 'Create initial achievements for the gamification system'

    def handle(self, *args, **options):
        achievements = [
            {
                'name': 'profile_complete',
                'description': 'Complete your profile with name and email',
                'category': 'profile',
                'icon': '👤',
                'points': 50
            },
            {
                'name': 'first_login',
                'description': 'Welcome to Addis Temari! First login completed',
                'category': 'milestone',
                'icon': '🎉',
                'points': 25
            },
            {
                'name': 'favorite_collector',
                'description': 'Add 5 universities to your favorites',
                'category': 'university',
                'icon': '⭐',
                'points': 75
            },
            {
                'name': 'first_application',
                'description': 'Mark your first university as applied',
                'category': 'application',
                'icon': '📝',
                'points': 100
            },
            {
                'name': 'application_master',
                'description': 'Apply to 10 universities',
                'category': 'application',
                'icon': '🎯',
                'points': 200
            },
            {
                'name': 'first_acceptance',
                'description': 'Get your first university acceptance!',
                'category': 'milestone',
                'icon': '🎊',
                'points': 300
            },
            {
                'name': 'explorer',
                'description': 'Browse 50 different universities',
                'category': 'university',
                'icon': '🔍',
                'points': 100
            },
            {
                'name': 'dedicated_student',
                'description': 'Use the platform for 7 consecutive days',
                'category': 'milestone',
                'icon': '🔥',
                'points': 150
            },
            {
                'name': 'scholarship_hunter',
                'description': 'View scholarship information for 10 universities',
                'category': 'university',
                'icon': '💰',
                'points': 125
            },
            {
                'name': 'visa_ready',
                'description': 'Mark a university as visa approved',
                'category': 'milestone',
                'icon': '✈️',
                'points': 500
            }
        ]

        created_count = 0
        for ach_data in achievements:
            achievement, created = Achievement.objects.get_or_create(
                name=ach_data['name'],
                defaults=ach_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created achievement: {achievement.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} achievements')
        )
from django.apps import AppConfig

class GamificationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gamification'
    
    def ready(self):
        # Temporarily disable signals for better performance
        # import gamification.signals
        pass
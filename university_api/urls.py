"""
URL configuration for university_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path
from universities.views import PaymentWebhookView

from rest_framework.routers import DefaultRouter
from contacts.views import ContactViewSet
from universities import views as university_views
from profiles import views as profiles_views

router = DefaultRouter()
# Register the UserViewSet from the universities app. This provides the /api/users/ endpoint.
router.register(r'users', university_views.UserViewSet, basename='user')
router.register(r'contacts', ContactViewSet, basename='contact')

# Group all API endpoints under a single prefix for clarity and better organization.
api_urlpatterns = [
    path('', include('universities.urls')),
    path('submit-application/', profiles_views.submit_application_draft, name='submit_application_draft'),
    path('', include('profiles.urls')),
    path('', include('notifications.urls')),
    path('creator/', include('content_creator.urls')),
    path('payments/', include('payments.urls')),
    path('gamification/', include('gamification.urls')),
    path('emails/', include('emails.urls')),
    path('', include(router.urls)), # for contacts app
]

urlpatterns = [
    path('admin/', admin.site.urls),
    # The webhook is kept at the root to ensure it's easily reachable by external services.
    re_path(r'^api/chapa-webhook/?$', PaymentWebhookView.as_view(), name='chapa_webhook'),
    # All other API urls are now included under the 'api/' prefix.
    path('api/', include(api_urlpatterns))
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

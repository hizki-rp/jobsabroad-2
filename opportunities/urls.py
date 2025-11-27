from django.urls import path
from . import views, admin_views

urlpatterns = [
    # Public opportunity endpoints
    path('', views.OpportunityListView.as_view(), name='opportunity-list'),
    path('<int:pk>/', views.OpportunityDetailView.as_view(), name='opportunity-detail'),
    path('<int:opportunity_id>/subscribe/', views.subscribe_from_opportunity, name='subscribe-from-opportunity'),
    
    # Creator endpoints
    path('create/', views.OpportunityCreateView.as_view(), name='opportunity-create'),
    path('my-opportunities/', views.MyOpportunitiesView.as_view(), name='my-opportunities'),
    path('creator-dashboard/', views.CreatorDashboardView.as_view(), name='creator-dashboard'),
    path('<int:opportunity_id>/stats/', views.opportunity_stats, name='opportunity-stats'),
    
    # Creator application endpoints
    path('creator-application/status/', admin_views.creator_application_status, name='creator-application-status'),
    path('creator-application/apply/', admin_views.CreatorApplicationCreateView.as_view(), name='creator-application-apply'),
    
    # Admin creator application endpoints
    path('admin/creator-applications/settings/', admin_views.AdminCreatorApplicationSettingsView.as_view(), name='admin-creator-application-settings'),
    path('admin/creator-applications/', admin_views.AdminCreatorApplicationListView.as_view(), name='admin-creator-applications'),
    path('admin/creator-applications/<int:application_id>/review/', admin_views.admin_review_application, name='admin-review-application'),
    
    # Admin opportunity endpoints
    path('admin/opportunities/', views.AdminOpportunityListView.as_view(), name='admin-opportunities'),
    path('admin/opportunities/<int:opportunity_id>/approve/', views.admin_approve_opportunity, name='admin-approve-opportunity'),
]
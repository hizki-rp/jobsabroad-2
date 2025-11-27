from django.urls import path
from . import views

urlpatterns = [
    # Email Templates
    path('templates/', views.EmailTemplateListCreateView.as_view(), name='email-template-list'),
    path('templates/<int:pk>/', views.EmailTemplateRetrieveUpdateDestroyView.as_view(), name='email-template-detail'),
    
    # Email Logs
    path('logs/', views.EmailLogListView.as_view(), name='email-log-list'),
    
    # Bulk Emails
    path('bulk/', views.BulkEmailListCreateView.as_view(), name='bulk-email-list'),
    
    # User Selection
    path('users/', views.UserEmailListView.as_view(), name='user-email-list'),
    
    # Email Actions
    path('send-single/', views.send_single_email, name='send-single-email'),
    path('send-bulk/', views.send_bulk_email, name='send-bulk-email'),
    path('send-template/', views.send_template_email, name='send-template-email'),
    
    # Statistics
    path('statistics/', views.email_statistics, name='email-statistics'),
    
    # Test
    path('test-config/', views.test_email_config, name='test-email-config'),
]




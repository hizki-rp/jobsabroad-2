from django.urls import path
from . import views

urlpatterns = [
    path('settings/', views.ApplicationSettingsView.as_view(), name='application-settings'),
    path('apply/', views.CreateCreatorApplicationView.as_view(), name='create-application'),
    path('posts/', views.OpportunityPostListView.as_view(), name='opportunity-posts'),
    path('posts/create/', views.CreateOpportunityPostView.as_view(), name='create-post'),
    path('posts/<int:pk>/', views.OpportunityPostDetailView.as_view(), name='post-detail'),
    path('posts/<int:pk>/update/', views.UpdateOpportunityPostView.as_view(), name='update-post'),
    path('posts/<int:post_id>/subscribe/', views.subscribe_to_creator_post, name='subscribe-to-post'),
    path('drafts/', views.DraftPostListView.as_view(), name='draft-posts'),
    path('dashboard/', views.creator_dashboard, name='creator-dashboard'),
]
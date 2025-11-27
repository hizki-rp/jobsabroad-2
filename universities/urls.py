from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'job-sites', views.CountryJobSiteViewSet, basename='jobsite')

urlpatterns = [
    # Authentication
    path('token/', views.MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('register/', views.CreateUserView.as_view(), name='register'),

    # This single path now handles both GET (retrieve) and PUT/PATCH (update) for a university.
    # It replaces the old `get_university_detail` and `update_university` paths.
    path('universities/<int:pk>/', views.UniversityRetrieveUpdateView.as_view(), name='university-detail'),

    # University Management (Admin)
    path('universities/create/', views.create_university, name='university-create'),
    path('universities/<int:pk>/delete/', views.delete_university, name='university-delete'),
    path('universities/bulk_create/', views.UniversityBulkCreate.as_view(), name='university-bulk-create'),
    path('universities/scrape/', views.UniversityScrapeView.as_view(), name='university-scrape'),
    path('universities/seed_from_api/', views.UniversitySeedFromAPI.as_view(), name='university-seed-from-api'),

    # Public/User-facing University Views
    path('universities/', views.UniversityList.as_view(), name='university-list'),

    # User Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    # Payment
    path('initialize-payment/', views.InitializeChapaPaymentView.as_view(), name='initialize_payment'),

    # Admin specific
    path('groups/', views.GroupList.as_view(), name='group-list'),
    path('stats/', views.AdminStatsView.as_view(), name='admin-stats'),
    
    # Username suggestions
    path('suggest-username/', views.suggest_username, name='suggest-username'),
    
    # Scholarships
    path('scholarships/', views.get_scholarships, name='get-scholarships'),
    path('scholarship-results/', views.scholarship_results_list, name='scholarship-results'),
    path('create-sample-scholarships/', views.create_sample_scholarships, name='create-sample-scholarships'),
    
    # Bulk Email
    path('send-bulk-email/', views.send_bulk_email, name='send-bulk-email'),

    # Country Job Sites CRUD (DRF router)
    path('', include(router.urls)),
]
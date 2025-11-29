from django.urls import path
from . import views

urlpatterns = [
    path('initialize-payment/', views.initialize_payment, name='initialize-payment'),
    path('confirm/', views.confirm_payment, name='confirm-payment'),
    path('verify-subscription/', views.verify_and_update_subscription, name='verify-subscription'),
    path('recent/', views.recent_payments, name='recent_payments'),
    path('today/', views.todays_payments, name='todays_payments'),
]
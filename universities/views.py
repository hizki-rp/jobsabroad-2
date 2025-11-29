from django.shortcuts import render

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, viewsets, status, exceptions
from django.db.models import Count, Q
from django.contrib.auth.models import User, Group
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
import os
import uuid
import requests
import json
import hmac
import functools
import operator
import hashlib
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import requests_cache
from tenacity import retry, stop_after_attempt, wait_exponential
try:
    import extruct
except ImportError:
    extruct = None
from w3lib.html import get_base_url
import tldextract
import pycountry
from price_parser import Price
from scrapegraph_py import Client as SGAIClient
try:
    from crawl4ai import Crawler as C4Crawler
except Exception:
    C4Crawler = None

# Create your views here.

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from profiles.models import Profile
import random
from .models import University, UserDashboard, ScholarshipResult, CountryJobSite
from django.core.mail import send_mail
from django.conf import settings
from .permissions import HasActiveSubscription
from .serializers import (
    UniversitySerializer, UserSerializer, UserDetailSerializer, 
    UserDashboardSerializer, GroupSerializer, MyTokenObtainPairSerializer,
    ScholarshipResultSerializer, CountryJobSiteSerializer, ApplicationDraftSerializer
)
from rest_framework.pagination import PageNumberPagination
from rest_framework import filters as drf_filters
from .tasks import send_application_status_update_email
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import action
import time
from urllib.parse import urlparse
from .scholarship_service import ScholarshipOwlService
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from rest_framework_simplejwt.tokens import RefreshToken
from .models import ApplicationDraft

# Enable a simple HTTP cache to stabilize repeated scrapes
requests_cache.install_cache('scrape_cache', backend='sqlite', expire_after=86400)

# Resilient network fetch with retries/backoff
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=1, max=4))
def fetch_url(url):
    return requests.get(url, timeout=20)

# Optional ScrapeGraphAI provider

def _scrape_with_sgai(url: str) -> dict:
    api_key = os.environ.get('SGAI_API_KEY')
    if not api_key:
        raise RuntimeError('SGAI_API_KEY not set in environment')
    client = SGAIClient(api_key=api_key)
    prompt = (
        'Extract university data as a single JSON object with exactly these keys: '
        'name, country, city, course_offered, application_fee, tuition_fee, intakes, '
        'bachelor_programs, masters_programs, scholarships, university_link, application_link, description. '
        'Fees should be numeric. Programs and scholarships should be arrays. '
        'Do not include explanations; only return pure JSON.'
    )
    data = client.smartscraper(website_url=url, user_prompt=prompt)
    if isinstance(data, dict):
        return data
    try:
        return json.loads(str(data))
    except Exception:
        return {}

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate JWT token for the new user
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': serializer.data,
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }, status=status.HTTP_201_CREATED)

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited by an admin.
    """
    queryset = User.objects.prefetch_related('groups', 'user_permissions').select_related('dashboard').all().order_by('-date_joined')
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserSerializer
        return UserDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        detail_serializer = UserDetailSerializer(user, context={'request': request})
        headers = self.get_success_headers(detail_serializer.data)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_scholarships(request):
    """Get scholarships from ScholarshipOwl API"""
    country = request.GET.get('country', '')
    limit = int(request.GET.get('limit', 10))
    
    service = ScholarshipOwlService()
    scholarships = service.get_scholarships(country=country, limit=limit)
    formatted = service.format_for_university(scholarships)
    
    # Save to database for admin viewing
    if scholarships:
        ScholarshipResult.objects.create(
            country=country,
            scholarships_data=formatted,
            total_count=len(formatted)
        )
    
    return Response({'scholarships': formatted})

class CountryJobSiteViewSet(viewsets.ModelViewSet):
    queryset = CountryJobSite.objects.all()
    serializer_class = CountryJobSiteSerializer
    permission_classes = [AllowAny]  # Allow anyone to view country job sites
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter]
    filterset_fields = { 'country': ['exact', 'icontains'] }
    search_fields = ['country', 'site_name']

@api_view(['GET'])
@permission_classes([AllowAny])
def popular_countries(request):
    """Get popular countries (countries with most job sites)"""
    from django.db.models import Count
    
    # Get countries with job sites, ordered by count
    countries = CountryJobSite.objects.values('country').annotate(
        site_count=Count('id')
    ).order_by('-site_count')[:10]  # Top 10 countries
    
    return Response({
        'popular_countries': list(countries)
    })

@api_view(['GET'])
@permission_classes([IsAdminUser])
def scholarship_results_list(request):
    """List all ScholarshipOwl API results for admin"""
    try:
        results = ScholarshipResult.objects.all().order_by('-fetched_at')
        data = []
        for result in results:
            data.append({
                'id': result.id,
                'country': result.country,
                'total_count': result.total_count,
                'fetched_at': result.fetched_at.isoformat(),
                'scholarships_data': result.scholarships_data
            })
        return Response(data)
    except Exception as e:
        # Return empty list if table doesn't exist or other error
        return Response([])

@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_sample_scholarships(request):
    """Create sample scholarship data for testing"""
    sample_data = [
        {
            'name': 'Merit Scholarship for International Students',
            'coverage': 'Full tuition',
            'eligibility': 'GPA 3.5+, International students',
            'link': 'https://example.com/scholarship1'
        },
        {
            'name': 'STEM Excellence Award',
            'coverage': '$10,000',
            'eligibility': 'STEM majors, US citizens',
            'link': 'https://example.com/scholarship2'
        }
    ]
    
    ScholarshipResult.objects.create(
        country='Canada',
        scholarships_data=sample_data,
        total_count=len(sample_data)
    )
    
    return Response({'message': 'Sample data created'})

@api_view(['POST'])
@permission_classes([IsAdminUser]) # Example: Only admins can create
def create_university(request):
    serializer = UniversitySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_university(request, pk):
    try:
        university = University.objects.get(id=pk)
        university.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except University.DoesNotExist:
        return Response({'error': 'University not found'}, status=status.HTTP_404_NOT_FOUND)

class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # get_or_create ensures a dashboard exists if the signal failed for some reason
        dashboard, created = UserDashboard.objects.get_or_create(user=request.user)
        
        # Superusers bypass subscription checks - automatically set them as active
        if request.user.is_superuser:
            if dashboard.subscription_status != 'active' or not dashboard.is_verified:
                dashboard.subscription_status = 'active'
                dashboard.is_verified = True
                if not dashboard.subscription_end_date:
                    from django.utils import timezone
                    from datetime import timedelta
                    dashboard.subscription_end_date = timezone.now().date() + timedelta(days=365)
                dashboard.save()
                print(f"Superuser {request.user.username} automatically granted active subscription")
        else:
            # Check if user has successful payments but subscription isn't active
            # This can happen if payment was processed but subscription wasn't updated
            from payments.models import Payment
            from django.utils import timezone
            from datetime import timedelta
            
            # Check for successful payments - check all time, not just recent
            successful_payments = Payment.objects.filter(
                user=request.user,
                status='success'
            ).order_by('-payment_date')
            
            # Also check for ANY payments (regardless of status) within last 48 hours
            # This handles cases where webhook hasn't processed yet or payment status wasn't set
            recent_payments = Payment.objects.filter(
                user=request.user,
                payment_date__gte=timezone.now() - timedelta(hours=48)
            ).order_by('-payment_date')
            
            # Also check for payments by user email (in case payment was created with email but user wasn't linked)
            # This is a fallback for edge cases
            if not successful_payments.exists() and not recent_payments.exists():
                # Try to find payments by matching email in tx_ref or other fields
                user_email_payments = Payment.objects.filter(
                    payment_date__gte=timezone.now() - timedelta(hours=48)
                )
                # Check if any payment's user email matches
                for p in user_email_payments:
                    if p.user and p.user.email == request.user.email:
                        recent_payments = Payment.objects.filter(id=p.id)
                        break
            
            print(f"Dashboard check for user {request.user.username} (ID: {request.user.id}, Email: {request.user.email}):")
            print(f"  - Successful payments: {successful_payments.count()}")
            print(f"  - Recent payments (48h): {recent_payments.count()}")
            print(f"  - Current subscription_status: {dashboard.subscription_status}")
            print(f"  - Current subscription_end_date: {dashboard.subscription_end_date}")
            print(f"  - Current total_paid: {dashboard.total_paid}")
            print(f"  - Current months_subscribed: {dashboard.months_subscribed}")
            print(f"  - Current is_verified: {dashboard.is_verified}")
            
            # If user has successful payments but subscription isn't active, update it
            payment_to_use = None
            if successful_payments.exists():
                payment_to_use = successful_payments.first()
                print(f"  - Using successful payment: {payment_to_use.tx_ref}, amount: {payment_to_use.amount}, date: {payment_to_use.payment_date}")
            elif recent_payments.exists():
                # If no successful payments but recent payment exists, check if we should update
                # This handles edge cases where payment was just made
                payment_to_use = recent_payments.first()
                print(f"  - Found recent payment: {payment_to_use.tx_ref}, status: {payment_to_use.status}, amount: {payment_to_use.amount}, date: {payment_to_use.payment_date}")
                # Update if payment is recent (within last 48 hours) - more lenient to catch delayed webhooks
                if payment_to_use and (timezone.now() - payment_to_use.payment_date).total_seconds() < 172800:  # 48 hours
                    # Mark payment as success if it's recent (webhook might be delayed)
                    if payment_to_use.status != 'success':
                        payment_to_use.status = 'success'
                        payment_to_use.save()
                        print(f"  - Marked recent payment {payment_to_use.tx_ref} as success for user {request.user.username}")
            
            # If no payment found but subscription is 'none' and user just logged in, check ApplicationDraft for payment info
            if not payment_to_use and dashboard.subscription_status == 'none':
                from universities.models import ApplicationDraft
                # Check for recent drafts that might indicate payment was made
                recent_drafts = ApplicationDraft.objects.filter(
                    email=request.user.email
                ).order_by('-created_at')[:5]
                
                if recent_drafts.exists():
                    print(f"  - Found {recent_drafts.count()} recent application drafts for user")
                    # If user has a draft with payment_tx_ref, payment might have been processed
                    for draft in recent_drafts:
                        if draft.payment_tx_ref:
                            # Try to find payment by tx_ref
                            from payments.models import Payment
                            payment_by_ref = Payment.objects.filter(tx_ref=draft.payment_tx_ref).first()
                            if payment_by_ref:
                                payment_to_use = payment_by_ref
                                print(f"  - Found payment via draft tx_ref: {payment_to_use.tx_ref}")
                                break
                            else:
                                # Payment doesn't exist but draft has tx_ref - create payment record
                                payment_to_use = Payment.objects.create(
                                    user=request.user,
                                    amount=500.00,
                                    tx_ref=draft.payment_tx_ref,
                                    status='success',
                                    payment_date=timezone.now()
                                )
                                print(f"  - Created payment record from draft tx_ref: {payment_to_use.tx_ref}")
                                break
            
            # Check if payment exists and hasn't been processed yet
            if payment_to_use:
                print(f"  - Payment found: {payment_to_use.tx_ref}")
                print(f"  - Payment subscription_updated: {payment_to_use.subscription_updated}")
                print(f"  - Subscription status: {dashboard.subscription_status}, End date: {dashboard.subscription_end_date}")
                
            # Update subscription if payment exists AND hasn't been processed yet
            if payment_to_use and not payment_to_use.subscription_updated:
                try:
                    # Refresh dashboard from DB to get latest state
                    dashboard.refresh_from_db()
                    print(f"  - Before update: status={dashboard.subscription_status}, end_date={dashboard.subscription_end_date}")
                    
                    # Use update_subscription method
                    amount = payment_to_use.amount
                    months_added = dashboard.update_subscription(amount, monthly_price=500)
                    
                    # Mark payment as processed
                    payment_to_use.subscription_updated = True
                    payment_to_use.save()
                    print(f"  - Marked payment as processed (subscription_updated=True)")
                    
                    # Refresh to confirm
                    dashboard.refresh_from_db()
                    print(f"  - After update: status={dashboard.subscription_status}, end_date={dashboard.subscription_end_date}")
                    print(f"  - After update: total_paid={dashboard.total_paid}, months_subscribed={dashboard.months_subscribed}, is_verified={dashboard.is_verified}")
                    
                except Exception as e:
                    print(f"  - ERROR updating subscription from existing payment: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Fallback - directly set fields
                    from decimal import Decimal
                    amount = Decimal(str(payment_to_use.amount)) if payment_to_use else Decimal('500.00')
                    dashboard.total_paid = Decimal(str(dashboard.total_paid)) + amount
                    dashboard.months_subscribed += 1
                    dashboard.subscription_status = 'active'
                    dashboard.is_verified = True
                    if not dashboard.subscription_end_date or dashboard.subscription_end_date < timezone.now().date():
                        dashboard.subscription_end_date = timezone.now().date() + timedelta(days=30)
                    else:
                        dashboard.subscription_end_date = dashboard.subscription_end_date + timedelta(days=30)
                    dashboard.save()
                    
                    # Mark payment as processed
                    payment_to_use.subscription_updated = True
                    payment_to_use.save()
                    
                    print(f"  - Used fallback to activate subscription for user {request.user.username}")
            
            # If payment was already processed but subscription isn't active, fix it
            elif payment_to_use and payment_to_use.subscription_updated and dashboard.subscription_status != 'active':
                print(f"  - Payment already processed but subscription not active, fixing...")
                dashboard.subscription_status = 'active'
                dashboard.is_verified = True
                if not dashboard.subscription_end_date:
                    dashboard.subscription_end_date = timezone.now().date() + timedelta(days=30)
                dashboard.save()
                print(f"  - Fixed subscription status to active")
        
        serializer = UserDashboardSerializer(dashboard)
        response_data = serializer.data
        
        # Get user's profile country
        user_country = None
        try:
            if hasattr(request.user, 'profile') and request.user.profile.country:
                user_country = request.user.profile.country
        except Exception:
            pass
        
        # Get job sites filtered by user's country
        job_sites = []
        if user_country:
            # Try exact match first, then case-insensitive contains
            job_sites = CountryJobSite.objects.filter(
                country__iexact=user_country
            ).values('id', 'country', 'site_name', 'site_url')
            if not job_sites.exists():
                # Fallback to case-insensitive contains
                job_sites = CountryJobSite.objects.filter(
                    country__icontains=user_country
                ).values('id', 'country', 'site_name', 'site_url')
        
        response_data['country'] = user_country
        response_data['job_sites'] = list(job_sites)
        
        return Response(response_data)

    def post(self, request):
        dashboard, created = UserDashboard.objects.get_or_create(user=request.user)
        university_id = request.data.get('university_id')
        list_name = request.data.get('list_name')

        if not university_id or not list_name:
            return Response({'error': 'university_id and list_name are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            university = University.objects.get(id=university_id)
        except University.DoesNotExist:
            return Response({'error': 'University not found'}, status=status.HTTP_404_NOT_FOUND)

        valid_lists = ['favorites', 'planning_to_apply', 'applied', 'accepted', 'visa_approved']
        if list_name not in valid_lists:
            return Response({'error': f'Invalid list name: {list_name}'}, status=status.HTTP_400_BAD_REQUEST)

        list_to_modify = getattr(dashboard, list_name)
        list_to_modify.add(university)

        # Trigger email notification for meaningful status changes
        if list_name in ['applied', 'accepted', 'visa_approved']:
            send_application_status_update_email.delay(request.user.id, university.name, list_name)


        serializer = UserDashboardSerializer(dashboard)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        dashboard, created = UserDashboard.objects.get_or_create(user=request.user)
        university_id = request.data.get('university_id')
        list_name = request.data.get('list_name')

        if not university_id or not list_name:
            return Response({'error': 'university_id and list_name are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            university = University.objects.get(id=university_id)
        except University.DoesNotExist:
            return Response({'error': 'University not found'}, status=status.HTTP_404_NOT_FOUND)

        valid_lists = ['favorites', 'planning_to_apply', 'applied', 'accepted', 'visa_approved']
        if list_name not in valid_lists:
            return Response({'error': f'Invalid list name: {list_name}'}, status=status.HTTP_400_BAD_REQUEST)

        list_to_modify = getattr(dashboard, list_name)
        list_to_modify.remove(university)

        serializer = UserDashboardSerializer(dashboard)
        return Response(serializer.data, status=status.HTTP_200_OK)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class UniversityList(generics.ListAPIView):
    # queryset is defined in get_queryset to allow for dynamic filtering
    serializer_class = UniversitySerializer
    permission_classes = [IsAuthenticated, HasActiveSubscription]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter]
    filterset_fields = {
        'country': ['icontains'],
        'city': ['icontains'],
        'course_offered': ['icontains'],
        'application_fee': ['lte'],
        'tuition_fee': ['lte'],
    }
    search_fields = ['name', 'country', 'course_offered']

    def dispatch(self, request, *args, **kwargs):
        # Ensure a dashboard exists for the user before permission checks.
        # This prevents a potential error in the `HasActiveSubscription`
        # permission class if the user has no dashboard record yet.
        if request.user and request.user.is_authenticated:
            UserDashboard.objects.get_or_create(user=request.user)
            Profile.objects.get_or_create(user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = University.objects.all()
        
        # Custom filter for country to handle US variations
        country_query = self.request.query_params.get('country__icontains')
        if country_query:
            if country_query.lower() in ['usa', 'us']:
                queryset = queryset.filter(
                    Q(country__icontains='United States') |
                    Q(country__icontains='USA') |
                    Q(country__icontains='US')
                )
            else:
                queryset = queryset.filter(country__icontains=country_query)
        
        # Custom filter for intakes JSONField with seasonal mapping
        intake_query = self.request.query_params.get('intake')
        if intake_query:
            # Map months to seasons and common intake terms
            month_to_season = {
                'January': ['January', 'Winter', 'Spring'],
                'February': ['February', 'Winter', 'Spring'], 
                'March': ['March', 'Spring'],
                'April': ['April', 'Spring'],
                'May': ['May', 'Spring', 'Summer'],
                'June': ['June', 'Summer'],
                'July': ['July', 'Summer'],
                'August': ['August', 'Summer', 'Fall'],
                'September': ['September', 'Fall', 'Autumn'],
                'October': ['October', 'Fall', 'Autumn'],
                'November': ['November', 'Fall', 'Autumn', 'Winter'],
                'December': ['December', 'Winter']
            }
            
            search_terms = month_to_season.get(intake_query, [intake_query])
            
            # Build query for multiple search terms
            intake_filter = Q()
            for term in search_terms:
                intake_filter |= Q(intakes__icontains=term)
            
            queryset = queryset.filter(intake_filter)
        return queryset.order_by('name')

class InitializeChapaPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        # For simplicity, we define a fixed amount for a 1-month subscription.
        # In a real app, this might come from a product model or settings.
        amount = "500"  # 500 ETB for 1 month

        # Generate a unique transaction reference, embedding the user ID.
        tx_ref = f"unifinder-{user.id}-{uuid.uuid4()}"

        chapa_secret_key = os.environ.get("CHAPA_SECRET_KEY")
        if not chapa_secret_key:
            return Response(
                {"status": "error", "message": "Chapa secret key is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        headers = {
            "Authorization": f"Bearer {chapa_secret_key}",
            "Content-Type": "application/json"
        }

        # The backend URL is the webhook Chapa will call.
        # The frontend URL is where the user is redirected after payment.
        # In production, request.build_absolute_uri can be unreliable behind proxies.
        # It's more robust to use an environment variable for the base URL.
        backend_base_url = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip('/')
        callback_url = backend_base_url + reverse('chapa_webhook')
        print(f"DEBUG: Webhook URL being sent to Chapa: {callback_url}")

        # Ensure no double slashes in the return URL and use an environment variable.
        frontend_base_url = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip('/')
        
        # Check if user already has a pending payment to prevent duplicates
        # Skip recent payment check for now to avoid errors
        # try:
        #     from payments.models import Payment
        #     recent_payment = Payment.objects.filter(
        #         user=user, 
        #         status='success',
        #         payment_date__gte=timezone.now() - timedelta(minutes=10)
        #     ).first()
        #     
        #     if recent_payment:
        #         return Response({
        #             "status": "error",
        #             "message": "You have already made a payment recently. Please wait before making another payment."
        #         }, status=status.HTTP_400_BAD_REQUEST)
        # except Exception as e:
        #     print(f"Error checking recent payments: {e}")
        #     # Continue with payment initialization if payment check fails
        
        # Check if user has active subscription to determine return URL
        dashboard, _ = UserDashboard.objects.get_or_create(user=user)
        if dashboard.subscription_status == 'expired' or not dashboard.subscription_end_date:
            # New user or expired subscription - redirect to payment success
            return_url = frontend_base_url + "/payment-success"
        else:
            # Existing subscriber - redirect to dashboard
            return_url = frontend_base_url + "/dashboard"
        payload = {
            "amount": amount,
            "currency": "ETB",
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "tx_ref": tx_ref,
            "callback_url": callback_url,
            "return_url": return_url,
            "customization[title]": "UNI-FINDER Subscription",
            "customization[description]": "1-Month Subscription Renewal",
        }

        try:
            chapa_init_url = "https://api.chapa.co/v1/transaction/initialize"
            print(f"DEBUG: Sending payment request to Chapa with callback: {callback_url}")
            print(f"DEBUG: Return URL: {return_url}")
            response = requests.post(chapa_init_url, headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()
            print(f"DEBUG: Chapa response: {response_data}")

            if response_data.get("status") == "success":
                return Response({
                    "status": "success",
                    "checkout_url": response_data.get("data", {}).get("checkout_url"),
                })
            else:
                return Response({
                    "status": "error",
                    "message": response_data.get("message", "Failed to initialize payment with Chapa.")
                }, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.RequestException as e:
            print(f"DEBUG: Chapa request failed: {e}")
            print(f"DEBUG: Response status: {e.response.status_code if hasattr(e, 'response') and e.response else 'No response'}")
            print(f"DEBUG: Response text: {e.response.text if hasattr(e, 'response') and e.response else 'No response'}")
            return Response({"status": "error", "message": f"Payment service error: {e}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"DEBUG: Unexpected error: {e}")
            return Response({"status": "error", "message": f"An unexpected error occurred: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def submit_application(request):
    """Accepts application form payload and stores it temporarily in ApplicationDraft."""
    data = request.data
    # Best-effort extraction of common fields
    email = data.get('email') or data.get('contact_email') or ''
    full_name = data.get('full_name') or (data.get('first_name','') + ' ' + data.get('last_name','')).strip()
    phone = data.get('phone') or data.get('phone_number') or ''
    country = data.get('country') or data.get('target_country') or ''
    tx_ref = data.get('payment_tx_ref') or ''

    draft = ApplicationDraft.objects.create(
        email=email,
        full_name=full_name,
        phone=phone,
        country=country,
        raw_payload=data,
        payment_tx_ref=tx_ref,
    )
    ser = ApplicationDraftSerializer(draft)
    # Return draft_id explicitly so frontend can reference it (don't return keys named `ok`/`status` to avoid overriding client-side response metadata)
    return Response({
        'draft_id': draft.id,
        'draft': ser.data,
    }, status=status.HTTP_201_CREATED)

class GroupList(generics.ListAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAdminUser]


class UniversityRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """
    Handles retrieving and updating a single university instance.
    GET requests are for viewing (requires subscription),
    PUT/PATCH requests are for updating (requires admin).
    """
    queryset = University.objects.all()
    serializer_class = UniversitySerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH']:
            return [IsAdminUser()]
        return [IsAuthenticated(), HasActiveSubscription()]

@method_decorator(csrf_exempt, name='dispatch')
class PaymentWebhookView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        # This GET handler is for debugging purposes.
        # You can visit this URL in your browser to check if it's reachable.
        # e.g., https://your-backend-domain.onrender.com/api/chapa-webhook/
        return Response({
            'status': 'ok',
            'message': 'Webhook URL is reachable. Ready to receive POST requests from Chapa.'
        }, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        # --- Enhanced Logging for Debugging ---
        print("=== CHAPA WEBHOOK RECEIVED ===")
        print(f"Method: {request.method}")
        print(f"Path: {request.path}")
        print(f"Headers: {dict(request.headers)}")
        print(f"Raw Body: {request.body.decode('utf-8', errors='ignore')}")
        print(f"Parsed Data: {request.data}")
        print(f"Environment CHAPA_WEBHOOK_SECRET exists: {bool(os.environ.get('CHAPA_WEBHOOK_SECRET'))}")
        # --- End Enhanced Logging ---

        # 1. Webhook Signature Verification
        chapa_webhook_secret = os.environ.get("CHAPA_WEBHOOK_SECRET")
        if not chapa_webhook_secret:
            print("Chapa webhook secret is not configured.")
            return Response({'status': 'error', 'message': 'Internal server error: Webhook secret not configured.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Chapa may send the signature in either of these headers. DRF headers are case-insensitive.
        chapa_signature = request.headers.get('Chapa-Signature')
        x_chapa_signature = request.headers.get('X-Chapa-Signature')

        if not chapa_signature and not x_chapa_signature:
            return Response({'status': 'error', 'message': 'Webhook signature not found.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            # Chapa's webhook signature seems to be based on a canonicalized JSON string,
            # not the raw request body. We will re-serialize the parsed data to match this.
            # Using separators=(',', ':') creates a compact JSON string without whitespace.
            payload_string = json.dumps(request.data, separators=(',', ':')).encode('utf-8')

            # Calculate the expected hash
            expected_hash = hmac.new(
                chapa_webhook_secret.encode('utf-8'),
                msg=payload_string,
                digestmod=hashlib.sha256
            ).hexdigest()

            # Check if either signature is valid
            chapa_sig_valid = chapa_signature and hmac.compare_digest(chapa_signature, expected_hash)
            x_chapa_sig_valid = x_chapa_signature and hmac.compare_digest(x_chapa_signature, expected_hash)

            if not (chapa_sig_valid or x_chapa_sig_valid):
                print(f"Signature mismatch. Expected: {expected_hash}")
                print(f"  Received Chapa-Signature: {chapa_signature}")
                print(f"  Received X-Chapa-Signature: {x_chapa_signature}")
                print(f"  Canonical JSON for signing: {payload_string.decode('utf-8', errors='ignore')}")
                return Response({'status': 'error', 'message': 'Invalid webhook signature.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        except Exception as e:
            print(f"Error during signature verification: {e}")
            return Response({'status': 'error', 'message': 'Internal server error during signature verification.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        print("✅ Webhook signature verified.")

        # Signature is valid, now we can proceed with the existing logic.
        # Chapa sends the full transaction detail in the POST body.
        webhook_data = request.data
        tx_ref = webhook_data.get('tx_ref')
        
        if not tx_ref:
            return Response({'status': 'error', 'message': 'Transaction reference not found in webhook payload.'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Check if the transaction was successful from the webhook payload.
        # This is safe because we have already verified the signature.
        if webhook_data.get("status") == "success":
            # 3. Process the payment
            user = None
            try:
                # tx_ref format: "unifinder-{user.id}-{uuid}"
                parts = tx_ref.split('-')
                if len(parts) >= 2 and parts[0] == 'unifinder':
                    user_id = int(parts[1])
                    user = User.objects.get(id=user_id)
                    print(f"Found user {user.username} (ID: {user_id}) from tx_ref: {tx_ref}")
                else:
                    print(f"tx_ref format doesn't match expected pattern: {tx_ref}")
                    # Try to find user by email from webhook data
                    email = webhook_data.get('email')
                    if email:
                        user = User.objects.filter(email=email).first()
                        if user:
                            print(f"Found user {user.username} by email: {email}")
            except (IndexError, ValueError, User.DoesNotExist) as e:
                print(f"Could not find user from tx_ref: {tx_ref}, error: {e}")
                # Try to find user by email from webhook data as fallback
                email = webhook_data.get('email')
                if email:
                    user = User.objects.filter(email=email).first()
                    if user:
                        print(f"Found user {user.username} by email fallback: {email}")
                    else:
                        print(f"Could not find user by email either: {email}")
                        return Response({'status': 'error', 'message': 'User not found for this transaction.'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({'status': 'error', 'message': 'Invalid transaction reference format and no email provided.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not user:
                return Response({'status': 'error', 'message': 'User not found for this transaction.'}, status=status.HTTP_400_BAD_REQUEST)

            # 4. Check for duplicate payment and record if new
            from payments.models import Payment
            existing_payment = Payment.objects.filter(tx_ref=tx_ref).first()
            if existing_payment:
                print(f"Payment {tx_ref} already exists. subscription_updated={existing_payment.subscription_updated}")
                dashboard, _ = UserDashboard.objects.get_or_create(user=user)
                dashboard.refresh_from_db()
                
                # Only update subscription if payment hasn't been processed yet
                if not existing_payment.subscription_updated:
                    print(f"  - Payment not processed yet, updating subscription...")
                    try:
                        months_added = dashboard.update_subscription(existing_payment.amount, monthly_price=500)
                        
                        # Mark payment as processed
                        existing_payment.subscription_updated = True
                        existing_payment.save()
                        
                        dashboard.refresh_from_db()
                        print(f"  - Updated subscription: status={dashboard.subscription_status}, end_date={dashboard.subscription_end_date}")
                    except Exception as e:
                        print(f"  - Error updating subscription for existing payment: {e}")
                        import traceback
                        traceback.print_exc()
                elif dashboard.subscription_status != 'active':
                    # Payment was processed but subscription not active - fix it
                    dashboard.subscription_status = 'active'
                    dashboard.is_verified = True
                    if not dashboard.subscription_end_date:
                        dashboard.subscription_end_date = timezone.now().date() + timedelta(days=30)
                    dashboard.save()
                    print(f"  - Fixed subscription status to active")
                
                return Response({'status': 'already processed'}, status=status.HTTP_200_OK)
            
            # Create payment with subscription_updated=True since we'll update it now
            payment = Payment.objects.create(
                user=user,
                amount=500.00,
                tx_ref=tx_ref,
                status='success',
                chapa_reference=webhook_data.get('reference', ''),
                subscription_updated=True  # Mark as processed immediately
            )
            
            # 5. Process payment and update subscription
            dashboard, _ = UserDashboard.objects.get_or_create(user=user)
            
            # Refresh dashboard to get latest state
            dashboard.refresh_from_db()
            print(f"Webhook processing payment for user {user.username} (ID: {user.id}):")
            print(f"  - Before update: status={dashboard.subscription_status}, end_date={dashboard.subscription_end_date}")
            print(f"  - Before update: total_paid={dashboard.total_paid}, months_subscribed={dashboard.months_subscribed}, is_verified={dashboard.is_verified}")
            
            # Process payment with update_subscription
            try:
                months_added = dashboard.update_subscription(500.00, monthly_price=500)
                
                # Refresh after update_subscription to get latest state
                dashboard.refresh_from_db()
                print(f"  - After update_subscription: months_added={months_added}")
                print(f"  - Result: status={dashboard.subscription_status}, end_date={dashboard.subscription_end_date}")
                print(f"  - Result: total_paid={dashboard.total_paid}, months_subscribed={dashboard.months_subscribed}, is_verified={dashboard.is_verified}")
                
            except Exception as e:
                print(f"Error updating subscription: {e}")
                import traceback
                traceback.print_exc()
                
                # Fallback - directly set fields
                from decimal import Decimal
                dashboard.total_paid = Decimal(str(dashboard.total_paid)) + Decimal('500.00')
                dashboard.months_subscribed += 1
                dashboard.subscription_status = 'active'
                dashboard.is_verified = True
                if not dashboard.subscription_end_date or dashboard.subscription_end_date < timezone.now().date():
                    dashboard.subscription_end_date = timezone.now().date() + timedelta(days=30)
                else:
                    dashboard.subscription_end_date = dashboard.subscription_end_date + timedelta(days=30)
                dashboard.save()
                print(f"Used fallback to activate subscription for user {user.username}")

            print(f"Successfully processed payment for user {user.id}. New expiry: {dashboard.subscription_end_date}")
            print(f"Payment recorded: {tx_ref} - 500 ETB")

            # 6. Conditional account creation & token generation based on ApplicationDraft
            try:
                draft = ApplicationDraft.objects.filter(payment_tx_ref=tx_ref).order_by('-created_at').first()
                if not draft:
                    draft = ApplicationDraft.objects.filter(email=user.email).order_by('-created_at').first()
            except Exception:
                draft = None

            if draft:
                # Create missing user by email if different flow sends webhook before explicit user exists
                UserModel = get_user_model()
                target_email = draft.email or user.email
                try:
                    target_user = UserModel.objects.get(email__iexact=target_email)
                except UserModel.DoesNotExist:
                    username_base = (target_email.split('@')[0] or f"user{user.id}")[:150]
                    username = username_base
                    i = 1
                    while UserModel.objects.filter(username__iexact=username).exists():
                        username = f"{username_base}{i}"
                        i += 1
                    temp_password = get_random_string(12)
                    target_user = UserModel.objects.create_user(
                        username=username,
                        email=target_email,
                        password=temp_password,
                        first_name=(draft.full_name or '').split(' ')[0][:150],
                        last_name=' '.join((draft.full_name or '').split(' ')[1:])[:150]
                    )
                    # Email the temporary password - DISABLED for performance
                    # Email sending disabled for now
                    # try:
                    #     send_mail(
                    #         subject="Your UNI-FINDER account",
                    #         message=f"Your account has been created. Temporary password: {temp_password}. Please log in and change it.",
                    #         from_email=settings.DEFAULT_FROM_EMAIL,
                    #         recipient_list=[target_email],
                    #         fail_silently=True
                    #     )
                    # except Exception:
                    #     pass
                # Generate JWT tokens for auto-login
                refresh = RefreshToken.for_user(target_user)
                auth_payload = {"refresh": str(refresh), "access": str(refresh.access_token)}
            else:
                # fallback to the payment user
                refresh = RefreshToken.for_user(user)
                auth_payload = {"refresh": str(refresh), "access": str(refresh.access_token)}

            # 5. Acknowledge receipt to Chapa with auth token hint
            return Response({'status': 'success', 'auth': auth_payload}, status=status.HTTP_200_OK)
        else:
            print(f"Webhook for tx_ref {tx_ref} was not successful. Status: {webhook_data.get('status')}")
            # Acknowledge receipt, but don't process.
            return Response({'status': 'received, not successful'}, status=status.HTTP_200_OK)

class AdminStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        total_users = User.objects.count()
        
        # Users who have applied to at least one university
        applied_users = User.objects.annotate(applied_count=Count('dashboard__applied')).filter(applied_count__gt=0).count()
        
        # Users logged in within the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        active_logins = User.objects.filter(last_login__isnull=False, last_login__gte=thirty_days_ago).count()
        
        # Users marked as inactive
        inactive_accounts = User.objects.filter(is_active=False).count()

        # University and Subscription stats
        total_universities = University.objects.count()
        active_subscriptions = UserDashboard.objects.filter(subscription_status='active').count()
        expired_subscriptions = UserDashboard.objects.filter(subscription_status='expired').count()

        stats = {
            'total_users': total_users,
            'applied_users': applied_users,
            'recent_logins': active_logins,
            'inactive_accounts': inactive_accounts,
            'total_universities': total_universities,
            'active_subscriptions': active_subscriptions,
            'expired_subscriptions': expired_subscriptions,
        }
        return Response(stats)

class UniversityBulkCreate(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        from django.db import connection
        
        file = request.FILES.get('file')
        json_text = request.data.get('json_text')

        if not file:
            if not json_text:
                return Response({'error': 'No file or JSON text provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            if file:
                data = json.load(file)
            else:
                data = json.loads(json_text)
            
            # Reset sequence to prevent ID conflicts
            with connection.cursor() as cursor:
                cursor.execute("SELECT setval(pg_get_serial_sequence('universities_university', 'id'), COALESCE(MAX(id), 1)) FROM universities_university;")
            
            # Process data and create universities directly
            created_universities = []
            skipped_count = 0
            
            if not isinstance(data, list):
                data = [data]
            
            for item in data:
                # Skip if university with same name AND country already exists
                name = item.get('name', '')
                country = item.get('country', '')
                if University.objects.filter(name=name, country=country).exists():
                    skipped_count += 1
                    continue
                
                # Create clean data without any id reference
                clean_data = {
                    'name': name,
                    'country': country,
                    'city': item.get('city', ''),
                    'course_offered': item.get('course_offered', ''),
                    'application_fee': item.get('application_fee', '0.00'),
                    'tuition_fee': item.get('tuition_fee', '0.00'),
                    'intakes': item.get('intakes', []),
                    'bachelor_programs': item.get('bachelor_programs', []),
                    'masters_programs': item.get('masters_programs', []),
                    'scholarships': item.get('scholarships', []),
                    'university_link': item.get('university_link', ''),
                    'application_link': item.get('application_link', ''),
                    'description': item.get('description', '')
                }
                
                # Create university directly without serializer to avoid any ID issues
                university = University.objects.create(**clean_data)
                created_universities.append(university)
            
            if not created_universities:
                return Response({'message': f'No new universities created. {skipped_count} already exist.'}, status=status.HTTP_200_OK)
            
            # Serialize the created universities for response
            serializer = UniversitySerializer(created_universities, many=True)
            return Response({
                'created': len(created_universities),
                'skipped': skipped_count,
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        except json.JSONDecodeError:
            return Response({'error': 'Invalid JSON format'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Bulk creation failed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

class UniversityScrapeView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Scrape a university website starting at `url` and return a structured JSON
        approximating the University schema. Enhanced heuristics:
        - Parse JSON-LD (schema.org) for name/address
        - Use meta tags (og:site_name, og:title)
        - Follow likely subpages (programs, tuition, scholarships)
        - Extract plausible tuition/application fees
        - Collect scholarship links and basic program lists
        - Infer country from JSON-LD or TLD where possible
        """
        start_url = request.data.get('url')
        if not start_url:
            return Response({'error': 'url is required'}, status=status.HTTP_400_BAD_REQUEST)
        provider = (request.data.get('provider') or '').lower()

        # Try ScrapeGraphAI first when explicitly requested
        if provider == 'sgai':
            try:
                sg = _scrape_with_sgai(start_url)
                # Normalize output to our expected structure
                def money(v):
                    try:
                        return f"{float(v):.2f}"
                    except Exception:
                        return "0.00"
                data = {
                    'id': None,
                    'name': sg.get('name') or '',
                    'country': sg.get('country') or '',
                    'city': sg.get('city') or '',
                    'course_offered': sg.get('course_offered') or '',
                    'application_fee': money(sg.get('application_fee')),
                    'tuition_fee': money(sg.get('tuition_fee')),
                    'intakes': sg.get('intakes') or [],
                    'bachelor_programs': sg.get('bachelor_programs') or [],
                    'masters_programs': sg.get('masters_programs') or [],
                    'scholarships': sg.get('scholarships') or [],
                    'university_link': sg.get('university_link') or start_url,
                    'application_link': sg.get('application_link') or start_url,
                    'description': sg.get('description') or '',
                    '_meta': {k: {'source': 'sgai', 'confidence': 0.9} for k in ['name','country','city','course_offered','application_fee','tuition_fee','intakes','bachelor_programs','masters_programs','scholarships','university_link','application_link','description']}
                }
                # Require minimum fields; otherwise fallback
                if data['name'] and data['country']:
                    return Response(data)
            except Exception:
                pass  # fall through to next provider

        # Try Crawl4AI (JS rendering) when requested
        if provider == 'c4ai' and C4Crawler is not None:
            try:
                crawler = C4Crawler(headless=True, timeout=30)
                html = None
                try:
                    page = crawler.open(start_url)
                    try:
                        page.wait_for_load_state('networkidle')
                    except Exception:
                        pass
                    html = page.content()
                finally:
                    try:
                        crawler.close()
                    except Exception:
                        pass
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    # Continue with aggregator resolution and built-in logic using this soup
                    resolved = _resolve_official_url(start_url, soup)
                    if resolved and resolved != start_url:
                        try:
                            crawler = C4Crawler(headless=True, timeout=30)
                            page2 = crawler.open(resolved)
                            try:
                                page2.wait_for_load_state('networkidle')
                            except Exception:
                                pass
                            html2 = page2.content()
                        finally:
                            try:
                                crawler.close()
                            except Exception:
                                pass
                        if html2:
                            start_url = resolved
                            soup = BeautifulSoup(html2, 'html.parser')
                    # From here, the built-in flow below will use this soup by bypassing fetch_url
                    # So we set a flag and jump to the built-in parsing section
                    # We'll reuse code by setting a variable
                    builtin_soup = soup
                else:
                    builtin_soup = None
            except Exception:
                builtin_soup = None
        else:
            builtin_soup = None

        try:
            if builtin_soup is None:
                resp = fetch_url(start_url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, 'html.parser')
            else:
                soup = builtin_soup
        except requests.RequestException as e:
            return Response({'error': f'Failed to fetch url: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        # If this looks like an aggregator (e.g., mastersportal), try to resolve the
        # official university website link and re-fetch that page for better accuracy.
        resolved = _resolve_official_url(start_url, soup)
        if resolved and resolved != start_url:
            try:
                resp2 = fetch_url(resolved)
                resp2.raise_for_status()
                start_url = resolved
                soup = BeautifulSoup(resp2.text, 'html.parser')
            except requests.RequestException:
                # If resolving fails, continue with the original page
                pass

        # JSON-LD and meta-based extraction
        ld = _parse_json_ld(soup, base_url=start_url)
        meta_name = _best_title(soup)
        h1 = soup.find('h1')
        name = ld.get('name') or (h1.get_text(strip=True) if h1 else None) or meta_name or urlparse(start_url).netloc

        address = ld.get('address') or {}
        if isinstance(address, dict):
            country = address.get('addressCountry') or address.get('addresscountry') or ''
            city = address.get('addressLocality') or address.get('addresslocality') or ''
        else:
            country = ''
            city = ''
        if not country:
            # fallback TLD guess
            country = _tld_country_guess(urlparse(start_url).netloc)

        # Application link
        anchors = soup.find_all('a', href=True)
        application_link = _pick_link(start_url, anchors, ['apply', 'admission', 'admissions', 'how to apply', 'apply now']) or start_url

        # Candidate pages to visit
        more_links = _collect_links_by_keywords(start_url, anchors, [
            'program', 'programs', 'courses', 'degrees', 'majors', 'undergraduate', 'graduate', 'tuition', 'fees', 'scholarship', 'financial aid'
        ])

        visited = set()
        text_blobs = [soup.get_text(" ", strip=True)]
        scholarships = []
        prog_candidates = []

        for link in more_links[:8]:
            if link in visited:
                continue
            visited.add(link)
            try:
                r = fetch_url(link)
                r.raise_for_status()
            except requests.RequestException:
                continue
            sp = BeautifulSoup(r.text, 'html.parser')
            text_blobs.append(sp.get_text(" ", strip=True))

            # Scholarship anchors
            if any(k in link.lower() for k in ['scholar', 'financial']):
                for a in sp.find_all('a', href=True):
                    t = (a.get_text() or '').strip()
                    if len(t) > 3 and ('scholar' in t.lower() or 'grant' in t.lower()):
                        scholarships.append({
                            'name': t,
                            'coverage': '',
                            'eligibility': '',
                            'link': urljoin(link, a['href'])
                        })

            # Program anchors
            for a in sp.find_all('a', href=True):
                t = (a.get_text() or '').strip()
                if len(t) < 4:
                    continue
                href = a['href'].lower()
                if any(k in href or k in t.lower() for k in ['program', 'degree', 'major', 'bachelor', 'master', 'msc', 'ba ', 'bs ', 'ma ', 'ms ']):
                    prog_candidates.append(t)

        big_text = "\n".join(text_blobs).lower()

        tuition_fee = _extract_currency_number(big_text, contexts=['tuition fee', 'tuition', 'fee'], min_value=500, max_value=100000)
        application_fee = _extract_currency_number(big_text, contexts=['application fee', 'application fees'], min_value=0, max_value=500)

        bachelors, masters = _classify_programs(prog_candidates)

        description = (
            (soup.find('meta', attrs={'name': 'description'}) or {}).get('content')
            or (soup.find('meta', attrs={'property': 'og:description'}) or {}).get('content')
            or (soup.find('title').get_text(strip=True) if soup.find('title') else '')
        )

        scholarships = _dedup_scholarships(scholarships)

        data = {
            'id': None,
            'name': name or '',
            'country': country or '',
            'city': city or '',
            'course_offered': '',
            'application_fee': f"{(application_fee or 0):.2f}",
            'tuition_fee': f"{(tuition_fee or 0):.2f}",
            'intakes': [],
            'bachelor_programs': bachelors[:25],
            'masters_programs': masters[:25],
            'scholarships': scholarships[:25],
            'university_link': start_url,
            'application_link': application_link,
            'description': description,
        }
        return Response(data)


class UniversitySeedFromAPI(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Seed universities by fetching candidates from Hipolabs Universities API, then
        scrape and insert if not existing. Limits by count and time.

        Body JSON:
        - country: optional string (e.g., "Canada")
        - limit: optional int (default 10, max 50)
        - max_seconds: optional int (default 60)
        """
        country = request.data.get('country')
        limit = int(request.data.get('limit') or 10)
        max_seconds = int(request.data.get('max_seconds') or 60)
        limit = max(1, min(limit, 50))

        source = (request.data.get('source') or 'hipo_api').lower()
        items = []
        if source == 'hipo_github':
            try:
                gh_resp = fetch_url('https://raw.githubusercontent.com/Hipo/university-domains-list/master/world_universities_and_domains.json')
                gh_resp.raise_for_status()
                all_items = gh_resp.json()
                if country:
                    items = [it for it in all_items if (it.get('country') or '').strip().lower() == country.strip().lower()]
                else:
                    items = all_items
            except Exception as e:
                return Response({'error': f'Failed to fetch GitHub universities list: {e}'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            params = {}
            if country:
                params['country'] = country
            try:
                api_resp = fetch_url('http://universities.hipolabs.com/search' + ('' if not params else '?' + requests.compat.urlencode(params)))
                api_resp.raise_for_status()
                items = api_resp.json()
            except Exception as e:
                return Response({'error': f'Failed to query Hipolabs API: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        start_time = time.time()
        processed = 0
        skipped_existing = 0
        created = 0
        errors = []

        existing = list(University.objects.all().values('id', 'name', 'university_link'))
        existing_names = {e['name'].strip().lower() for e in existing if e['name']}
        existing_domains = set()
        for e in existing:
            try:
                d = urlparse(e['university_link']).netloc.lower()
                if d:
                    existing_domains.add(d)
            except Exception:
                pass

        for it in items:
            if time.time() - start_time > max_seconds:
                break
            if processed >= limit:
                break

            name = (it.get('name') or '').strip()
            country_it = (it.get('country') or '').strip()
            home = None
            try:
                web_pages = it.get('web_pages') or []
                if web_pages:
                    home = web_pages[0]
            except Exception:
                home = None

            if not name or not home:
                continue

            # existence check by name or domain
            dom = ''
            try:
                dom = urlparse(home).netloc.lower()
            except Exception:
                pass
            if name.lower() in existing_names or (dom and dom in existing_domains):
                skipped_existing += 1
                processed += 1
                continue

            # scrape to enrich
            try:
                req = request._request  # underlying Django request, not needed here
                # Reuse internal logic by calling our own method directly
                sreq = request
                sreq._full_data = {'url': home}
                scrape_view = UniversityScrapeView()
                data_resp = scrape_view.post(request)
                if data_resp.status_code != 200:
                    raise Exception(f"scraper returned {data_resp.status_code}")
                data = data_resp.data
                # insert
                data['name'] = name or data.get('name') or ''
                data['country'] = country_it or data.get('country') or ''
                if not data.get('university_link'):
                    data['university_link'] = home
                ser = UniversitySerializer(data=data)
                ser.is_valid(raise_exception=True)
                ser.save()
                created += 1
            except Exception as e:
                errors.append({'name': name, 'url': home, 'error': str(e)})
            finally:
                processed += 1

        return Response({
            'total_fetched': len(items),
            'processed': processed,
            'skipped_existing': skipped_existing,
            'created': created,
            'errors': errors[:20],
            'duration_seconds': int(time.time() - start_time),
        })


def _resolve_official_url(start_url, soup):
    """
    Attempt to find an external 'official website' link on aggregator pages and return it.
    Currently supports mastersportal/bachelorsportal/phdportal pages heuristically.
    """
    try:
        host = urlparse(start_url).netloc.lower()
    except Exception:
        return None

    aggregators = ['mastersportal.com', 'bachelorsportal.com', 'phdportal.com', 'shortcoursesportal.com']
    if any(dom in host for dom in aggregators):
        for a in soup.find_all('a', href=True):
            text = (a.get_text() or '').strip().lower()
            href = a['href']
            full = urljoin(start_url, href)
            try:
                dom = urlparse(full).netloc.lower()
            except Exception:
                continue
            # pick first external link that looks like a website/official link
            if dom and not any(agg in dom for agg in aggregators):
                if 'website' in text or 'official' in text or 'visit' in text:
                    return full
    return None


def _parse_json_ld(soup, base_url=None):
    out = {}
    html = str(soup)
    try:
        if extruct is None:
            data = []
        else:
            data = extruct.extract(html, base_url=base_url or "", syntaxes=["json-ld"], uniform=True).get("json-ld", [])
    except Exception:
        data = []
    for obj in data:
        t = obj.get('@type')
        types = [t] if isinstance(t, str) else (t or [])
        types = [x.lower() for x in types if isinstance(x, str)]
        if any(x in types for x in ['collegeoruniversity', 'educationalorganization', 'organization']):
            out['name'] = obj.get('name') or out.get('name')
            addr = obj.get('address')
            if isinstance(addr, dict):
                out['address'] = {
                    'addressCountry': addr.get('addressCountry'),
                    'addressLocality': addr.get('addressLocality')
                }
            elif isinstance(addr, str):
                out['address'] = {'addressLocality': addr}
    return out


def _best_title(soup):
    metas = [
        soup.find('meta', attrs={'property': 'og:site_name'}),
        soup.find('meta', attrs={'property': 'og:title'}),
        soup.find('meta', attrs={'name': 'twitter:title'}),
    ]
    for m in metas:
        if m and m.get('content'):
            return m['content'].strip()
    t = soup.find('title')
    return t.get_text(strip=True) if t else ''


def _pick_link(base, anchors, keywords):
    for a in anchors:
        text = (a.get_text() or '').lower()
        href = a['href'].lower()
        if any(k in text or k in href for k in keywords):
            return urljoin(base, a['href'])
    return None


def _collect_links_by_keywords(base, anchors, keywords):
    out = []
    seen = set()
    for a in anchors:
        text = (a.get_text() or '').lower()
        href = a['href']
        if any(k in text or k in href.lower() for k in keywords):
            full = urljoin(base, href)
            if full not in seen:
                seen.add(full)
                out.append(full)
    return out


def _extract_currency_number(text, contexts, min_value=0, max_value=999999):
    best = None
    for ctx in contexts:
        for m in re.finditer(rf"{re.escape(ctx)}(.{{0,180}})", text, flags=re.IGNORECASE):
            snippet = m.group(1)
            # Try price-parser first
            try:
                p = Price.fromstring(snippet)
                if p and p.amount_float:
                    val = float(p.amount_float)
                    if min_value <= val <= max_value:
                        best = val if (best is None or val > best) else best
                        continue
            except Exception:
                pass
            # Fallback regex
            for n in re.finditer(r"(?:\$|usd|us\$|eur|€|gbp|£)?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,})(?:\.[0-9]{2})?", snippet, flags=re.IGNORECASE):
                try:
                    val = float(n.group(1).replace(',', ''))
                except Exception:
                    continue
                if min_value <= val <= max_value:
                    best = val if (best is None or val > best) else best
    return best


def _classify_programs(names):
    bachelors = []
    masters = []
    for t in names:
        low = t.lower()
        entry = {
            'program_name': t,
            'required_documents': [],
            'language': '',
            'duration_years': None,
            'notes': ''
        }
        if any(k in low for k in ['bachelor', ' bsc', ' ba ', ' beng']):
            bachelors.append(entry)
        elif any(k in low for k in ['master', ' msc', ' ms ', ' ma ', ' meng']):
            m = entry.copy()
            m['thesis_required'] = True
            masters.append(m)
    return bachelors, masters


def _dedup_scholarships(items):
    seen_links = set()
    seen_names = set()
    out = []
    for it in items:
        link = (it.get('link') or '').strip().lower()
        name = (it.get('name') or '').strip().lower()
        if not link and not name:
            continue
        if link in seen_links or name in seen_names:
            continue
        seen_links.add(link)
        seen_names.add(name)
        out.append(it)
    return out


def _tld_country_guess(hostname):
    ext = tldextract.extract(hostname)
    # ext.suffix may be like 'edu' or 'ca' or 'co.uk'
    parts = ext.suffix.split('.')
    code = parts[-1].upper() if parts else ''
    # Map common academic TLDs
    if code == 'EDU':
        return 'United States'
    if len(code) == 2:
        try:
            c = pycountry.countries.get(alpha_2=code)
            if c:
                return c.name
        except Exception:
            pass
    return ''

@api_view(['POST'])
@permission_classes([AllowAny])
def suggest_username(request):
    first_name = request.data.get('first_name', '').strip().lower()
    last_name = request.data.get('last_name', '').strip().lower()
    
    if not first_name:
        return Response({'suggestions': []}, status=status.HTTP_400_BAD_REQUEST)
    
    suggestions = []
    base_names = [
        first_name,
        f"{first_name}{last_name}" if last_name else first_name,
        f"{first_name}_{last_name}" if last_name else f"{first_name}_user",
    ]
    
    for base in base_names:
        for i in range(3):
            if i == 0:
                candidate = base
            else:
                candidate = f"{base}{random.randint(10, 999)}"
            
            if not User.objects.filter(username__iexact=candidate).exists():
                suggestions.append(candidate)
                if len(suggestions) >= 5:
                    break
        if len(suggestions) >= 5:
            break
    
    return Response({'suggestions': suggestions[:5]})

@api_view(['POST'])
@permission_classes([IsAdminUser])
def send_bulk_email(request):
    data = request.data
    subject = data.get('subject', '')
    message = data.get('message', '')
    user_ids = data.get('user_ids', [])
    send_to_all = data.get('send_to_all', False)
    
    if not subject or not message:
        return Response({'error': 'Subject and message are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        if send_to_all:
            users = User.objects.filter(is_active=True)
        else:
            users = User.objects.filter(id__in=user_ids, is_active=True)
        
        recipient_emails = [user.email for user in users if user.email]
        
        if not recipient_emails:
            return Response({'error': 'No valid email addresses found'}, status=status.HTTP_400_BAD_REQUEST)
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_emails,
            fail_silently=False,
        )
        
        return Response({
            'success': True,
            'message': f'Email sent to {len(recipient_emails)} users',
            'recipients_count': len(recipient_emails)
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
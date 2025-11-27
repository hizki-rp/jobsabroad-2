from rest_framework import serializers
from .models import University, UserDashboard, ScholarshipResult, CountryJobSite, ApplicationDraft
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import validate_email
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings
from profiles.models import Profile


class UserSerializer(serializers.ModelSerializer):
    # Add the email field so the serializer will accept it
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    phone_number = serializers.CharField(required=False, allow_blank=True, max_length=20, write_only=True)
    # Profile fields
    dob = serializers.DateField(required=False, allow_null=True, write_only=True)
    currentRole = serializers.CharField(required=False, allow_blank=True, max_length=100, write_only=True)
    yearsExperience = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    skills = serializers.CharField(required=False, allow_blank=True, write_only=True)
    country = serializers.CharField(required=False, allow_blank=True, max_length=100, write_only=True)
    # Job preference fields
    desiredStartDate = serializers.CharField(required=False, allow_blank=True, write_only=True)
    workPermitStatus = serializers.CharField(required=False, allow_blank=True, max_length=100, write_only=True)
    desiredSalary = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = User
        # Add 'email' to the list of fields
        fields = [
            "id", "username", "email", "password", "first_name", "last_name", 
            "phone_number", "dob", "currentRole", "yearsExperience", "skills", 
            "country", "desiredStartDate", "workPermitStatus", "desiredSalary"
        ]
        extra_kwargs = {"password": {"write_only": True}}

    def validate_username(self, value):
        # Check for case-insensitive username uniqueness
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Username taken")
        return value.lower()  # Store usernames in lowercase

    def create(self, validated_data):
        # Extract profile and job preference fields
        phone_number = validated_data.pop('phone_number', None)
        dob = validated_data.pop('dob', None)
        current_role = validated_data.pop('currentRole', None)
        years_experience = validated_data.pop('yearsExperience', None)
        skills_str = validated_data.pop('skills', None)
        country = validated_data.pop('country', None)
        desired_start_date_str = validated_data.pop('desiredStartDate', None)
        work_permit_status = validated_data.pop('workPermitStatus', None)
        desired_salary_str = validated_data.pop('desiredSalary', None)
        
        # Use create_user to properly hash the password
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        # Add user to the 'user' group by default on registration
        try:
            user_group = Group.objects.get(name='user')
            user.groups.add(user_group)
        except Group.DoesNotExist:
            # In a production app, you would ensure this group exists
            # via a migration or a management command.
            pass

        # Always create a profile for the new user. This is more robust than
        # relying on a signal, which might fail or not exist.
        profile, created = Profile.objects.get_or_create(user=user)
        
        # Update profile fields
        if phone_number:
            profile.phone_number = phone_number
        if dob:
            profile.dob = dob
        if current_role:
            profile.current_role = current_role
        if years_experience is not None:
            profile.years_experience = years_experience
        if skills_str:
            # Parse skills from comma-separated string to list
            skills_list = [skill.strip() for skill in skills_str.split(',') if skill.strip()]
            profile.skills = skills_list
        if country:
            profile.country = country
        profile.save()

        # Create or update job preferences
        from profiles.models import JobPreference
        job_preference, created = JobPreference.objects.get_or_create(profile=profile)
        if desired_start_date_str:
            # Parse month string (YYYY-MM) to date (first day of month)
            try:
                from datetime import datetime
                date_obj = datetime.strptime(desired_start_date_str, '%Y-%m').date()
                job_preference.desired_start_date = date_obj
            except (ValueError, TypeError):
                pass
        if work_permit_status:
            job_preference.work_permit_status = work_permit_status
        if desired_salary_str:
            # Try to parse salary string (remove currency symbols and extract number)
            try:
                import re
                # Extract numbers from string like "€50,000 - €70,000" or "50000"
                numbers = re.findall(r'[\d,]+', desired_salary_str.replace(',', ''))
                if numbers:
                    # Take the first number found
                    salary_value = float(numbers[0].replace(',', ''))
                    job_preference.desired_salary = salary_value
            except (ValueError, TypeError):
                pass
        job_preference.save()

        return user

class SafeDashboardField(serializers.Field):
    """
    A custom field to safely serialize the dashboard,
    handling cases where it might not exist for a user.
    """
    def to_representation(self, user_instance):
        try:
            dashboard = user_instance.dashboard
            return DashboardAdminSerializer(dashboard).data
        except ObjectDoesNotExist:
            # Catching the generic ObjectDoesNotExist will handle both
            # UserDashboard.DoesNotExist and the RelatedObjectDoesNotExist
            # that is raised when accessing user.dashboard for a user without one.
            return None

    def to_internal_value(self, data):
        return data

class DashboardAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDashboard
        fields = ['subscription_status', 'subscription_end_date']

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']

class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer for admins to view and edit user details, including subscriptions."""
    dashboard = SafeDashboardField(source='*', required=False)
    groups = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all()
     )

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "groups", "is_staff", "is_active", "date_joined", "dashboard"]
        read_only_fields = ["id", "username", "email", "date_joined", "is_staff"]
    
    def update(self, instance, validated_data):
        dashboard_data = validated_data.pop('dashboard', None)

        # Let the parent class handle the update for User model fields,
        # including M2M fields like 'groups'.
        # We pop 'dashboard' first as it's not a real model field and needs custom handling.
        instance = super().update(instance, validated_data)

        # Update nested dashboard subscription fields
        if dashboard_data:
            dashboard, _ = UserDashboard.objects.get_or_create(user=instance)
            dashboard.subscription_status = dashboard_data.get('subscription_status', dashboard.subscription_status)
            dashboard.subscription_end_date = dashboard_data.get('subscription_end_date', dashboard.subscription_end_date)
            dashboard.save()
            instance.refresh_from_db()

        return instance

class UniversitySerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = '__all__'
        extra_kwargs = {'id': {'read_only': True}}
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Temporarily exclude image_url if it doesn't exist in the database
        if 'image_url' in data:
            data.pop('image_url', None)
        return data

class DashboardUniversitySerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = ['id', 'name']

class UserDashboardSerializer(serializers.ModelSerializer):
    favorites = DashboardUniversitySerializer(many=True, read_only=True)
    planning_to_apply = DashboardUniversitySerializer(many=True, read_only=True)
    applied = DashboardUniversitySerializer(many=True, read_only=True)
    accepted = DashboardUniversitySerializer(many=True, read_only=True)
    visa_approved = DashboardUniversitySerializer(many=True, read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    should_prompt_payment = serializers.SerializerMethodField()

    def get_should_prompt_payment(self, obj):
        from django.utils import timezone
        user = obj.user
        
        # Admins and superusers never need to pay
        if user.is_superuser or user.is_staff or user.groups.filter(name='admin').exists():
            return False
        
        # Allow all users to access dashboard without payment requirement
        # Payment is optional for accessing premium features, not for basic dashboard access
        # Return False to allow dashboard access without payment prompt
        return False
        
        # Original payment check logic (commented out - can be re-enabled if needed)
        # # Fallback for existing users before migration
        # try:
        #     if not hasattr(obj, 'is_verified') or obj.is_verified is None:
        #         return not obj.subscription_end_date
        # except AttributeError:
        #     return not obj.subscription_end_date
        # 
        # # Check if user has verified active subscription
        # if obj.is_verified and obj.subscription_end_date and obj.subscription_end_date >= timezone.now().date():
        #     return False
        # 
        # # For existing users with subscription_end_date but no is_verified field
        # if obj.subscription_end_date and obj.subscription_end_date >= timezone.now().date():
        #     return False
        # 
        # return True

    class Meta:
        model = UserDashboard
        fields = ['first_name', 'last_name', 'favorites', 'planning_to_apply', 'applied', 'accepted', 'visa_approved', 'subscription_status', 'subscription_end_date', 'total_paid', 'months_subscribed', 'is_verified', 'should_prompt_payment']

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # The frontend can send either a username or an email in the 'username' field.
        username_or_email = attrs.get(self.username_field)
        password = attrs.get('password')
        user = None

        # Check if the input looks like an email
        try:
            validate_email(username_or_email)
            is_email = True
        except ValidationError:
            is_email = False

        if is_email:
            # Try to find a user with this email (case-insensitive).
            try:
                user_obj = User.objects.get(email__iexact=username_or_email)
                if user_obj.check_password(password):
                    user = user_obj
            except User.DoesNotExist:
                # Fall through to the default authentication method.
                pass

        # If not authenticated by email, or if it wasn't an email, try case-insensitive username authentication.
        if not user:
            try:
                user_obj = User.objects.get(username__iexact=username_or_email)
                if user_obj.check_password(password):
                    user = user_obj
            except User.DoesNotExist:
                pass

        if not user or not user.is_active:
            raise serializers.ValidationError('No active account found with the given credentials.')

        # Ensure UserDashboard exists (create if missing with default 'none' subscription status)
        dashboard, created = UserDashboard.objects.get_or_create(user=user)
        if created:
            print(f"Created UserDashboard for user {user.username} with default subscription status: {dashboard.subscription_status}")

        self.user = user

        refresh = self.get_token(self.user)

        data = {"refresh": str(refresh), "access": str(refresh.access_token)}

        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # The `get_or_create` is a safeguard in case the post_save signal for profile creation failed.
        profile, created = Profile.objects.get_or_create(user=user)
        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['is_staff'] = user.is_staff
        token['groups'] = list(user.groups.values_list('name', flat=True))

        # Safely get the profile picture URL.
        # This prevents errors in production if the file is missing from storage.
        try:
            token['profile_picture'] = profile.profile_picture.url if profile.profile_picture else None
        except (ValueError, AttributeError):
            token['profile_picture'] = None

        token['first_name'] = user.first_name
        token['last_name'] = user.last_name

        return token

class ScholarshipResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScholarshipResult
        fields = ['id', 'country', 'total_count', 'fetched_at', 'scholarships_data']

class CountryJobSiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CountryJobSite
        fields = ['id', 'country', 'site_name', 'site_url']
        read_only_fields = ['id']

class ApplicationDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationDraft
        fields = ['id', 'email', 'full_name', 'phone', 'country', 'raw_payload', 'payment_tx_ref', 'created_at']
        read_only_fields = ['id', 'created_at']
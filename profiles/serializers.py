# h:\Django2\UNI-FINDER-GIT\backend\profiles\serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, WorkExperience, JobPreference

# A read-only serializer for the user to be nested in the profile GET response
class UserDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'username')

class WorkExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkExperience
        exclude = ('profile',)

class JobPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPreference
        exclude = ('profile',)

class ProfileSerializer(serializers.ModelSerializer):
    # Use the read-only serializer for the 'user' field in GET responses
    user = UserDataSerializer(read_only=True)
    work_experiences = WorkExperienceSerializer(many=True, read_only=True)
    job_preference = JobPreferenceSerializer(read_only=True)
    
    # Add write-only fields to accept flat data for user updates during PATCH
    first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Profile
        fields = (
            'user', 'bio', 'phone_number', 'dob', 'current_role', 'years_experience',
            'skills', 'country', 'work_experiences', 'job_preference',
            'first_name', 'last_name'
        )
        read_only_fields = ('user',)

    def update(self, instance, validated_data):
        # The request is passed in the context by DRF's generic views
        request = self.context.get('request')
        user = instance.user

        # Update User model fields from the flat validated_data
        if 'first_name' in validated_data:
            user.first_name = validated_data.pop('first_name')
        if 'last_name' in validated_data:
            user.last_name = validated_data.pop('last_name')
        user.save()

        # Let super().update handle the regular Profile model fields
        return super().update(instance, validated_data)

class ProfileUpdateSerializer(serializers.ModelSerializer):
    """
    This serializer is used by the submit_application_draft view to update
    the profile with data from the onboarding form.
    """
    # Add fields for User creation
    work_experience = WorkExperienceSerializer(required=False)
    job_preference = JobPreferenceSerializer(required=False)

    email = serializers.EmailField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Profile
        # List all the fields from the frontend form that should be saved to the profile.
        fields = (
            # User fields
            'email', 'password', 'first_name', 'last_name',
            # Profile fields
            'phone_number', 'dob', 'current_role', 'years_experience',
            'skills', 'country',
            # Nested fields
            'work_experience', 'job_preference'
        )

    def create(self, validated_data):
        work_experience_data = validated_data.pop('work_experience', None)
        job_preference_data = validated_data.pop('job_preference', None)

        # Pop user data from the validated data
        user_data = {
            'username': validated_data['email'], # Use email as username
            'email': validated_data.pop('email'),
            'password': validated_data.pop('password'),
            'first_name': validated_data.pop('first_name', ''),
            'last_name': validated_data.pop('last_name', ''),
        }
        # Create the user
        user = User.objects.create_user(**user_data)
        
        # Create the profile with the remaining validated_data
        # The signal will create the profile, but we get it here to attach related objects
        profile = Profile.objects.get(user=user)
        for attr, value in validated_data.items():
            setattr(profile, attr, value)
        profile.save()
        
        if work_experience_data:
            WorkExperience.objects.create(profile=profile, **work_experience_data)
        
        if job_preference_data:
            JobPreference.objects.update_or_create(profile=profile, defaults=job_preference_data)
            
        return profile

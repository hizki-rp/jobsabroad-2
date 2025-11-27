# h:\Django2\UNI-FINDER-GIT\backend\profiles\views.py
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from .models import Profile
from .serializers import ProfileSerializer, ProfileUpdateSerializer

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    # Add parsers to handle multipart form data for file uploads
    parser_classes = (MultiPartParser, FormParser)

    def get_object(self):
        # get_or_create is robust for users who might not have a profile yet
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile

@api_view(['POST'])
@permission_classes([AllowAny]) # Allow unauthenticated users to create a profile
def submit_application_draft(request):
    """
    Receives application data from the multi-step form, creates a new user,
    and saves their profile information.
    """
    data = request.data.copy()

    # Transform flat form data into nested structures for the serializer.
    # This assumes work_experience and job_preference are sent as flat fields
    # and need to be grouped into dictionaries.
    work_experience_data = {
        'company_name': data.pop('company_name', [None])[0],
        'job_title': data.pop('job_title', [None])[0],
        'start_date': data.pop('start_date', [None])[0],
        'end_date': data.pop('end_date', [None])[0],
    }
    if any(work_experience_data.values()):
        data['work_experience'] = work_experience_data

    # The serializer will handle creating related objects from this nested data.
    # Initialize the serializer with the request data to create a new user and profile.
    # We are not passing an instance, so the serializer's .create() method will be called.
    serializer = ProfileUpdateSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        # Use 201 CREATED for successful resource creation.
        return Response({"message": "Application submitted successfully."}, status=status.HTTP_201_CREATED)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

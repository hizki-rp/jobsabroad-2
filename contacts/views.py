from rest_framework import viewsets, permissions, mixins
from .models import Contact
from .serializers import ContactSerializer

class IsAdminOrPostOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to view, but anyone to create (POST).
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_staff
        return True

class ContactViewSet(mixins.CreateModelMixin,
                     mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     viewsets.GenericViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsAdminOrPostOnly]
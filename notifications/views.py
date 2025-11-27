from django.utils import timezone
from django.db.models import Exists, OuterRef, Q, BooleanField, ExpressionWrapper
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import api_view, permission_classes

from .models import Notification, NotificationRead
from .serializers import NotificationSerializer


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # status param: active (default), unread, all
        status_filter = request.query_params.get('status', 'active')
        now = timezone.now()
        base_qs = Notification.objects.filter(is_active=True).exclude(
            Q(expires_at__isnull=False) & Q(expires_at__lt=now)
        )
        # audience scoping: ALL or CUSTOM recipients includes user
        qs = base_qs.filter(
            Q(audience=Notification.AUDIENCE_ALL) |
            Q(audience=Notification.AUDIENCE_CUSTOM, recipients=request.user)
        ).distinct()

        # annotate read status
        read_subq = NotificationRead.objects.filter(
            notification=OuterRef('pk'), user=request.user
        )
        qs = qs.annotate(
            is_read=ExpressionWrapper(
                Exists(read_subq), output_field=BooleanField()
            )
        )

        if status_filter == 'unread':
            qs = qs.filter(is_read=False)
        elif status_filter == 'all':
            pass  # no extra filter
        else:
            # active is default (already filtered by is_active and expiry)
            pass

        serializer = NotificationSerializer(qs[:50], many=True)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    # mark as read the notifications visible to this user
    now = timezone.now()
    visible = Notification.objects.filter(is_active=True).exclude(
        Q(expires_at__isnull=False) & Q(expires_at__lt=now)
    ).filter(
        Q(audience=Notification.AUDIENCE_ALL) |
        Q(audience=Notification.AUDIENCE_CUSTOM, recipients=request.user)
    )
    # bulk create read rows ignoring duplicates
    to_create = []
    existing = set(
        NotificationRead.objects.filter(user=request.user, notification__in=visible)
        .values_list('notification_id', flat=True)
    )
    for nid in visible.values_list('id', flat=True):
        if nid not in existing:
            to_create.append(NotificationRead(user=request.user, notification_id=nid))
    if to_create:
        NotificationRead.objects.bulk_create(to_create, ignore_conflicts=True)
    return Response({'status': 'ok'})

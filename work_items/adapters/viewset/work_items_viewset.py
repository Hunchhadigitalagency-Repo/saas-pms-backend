from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from project.permission import ProjectAccessPermission
from customer.models import ActiveClient, UserClientRole
from pms.jwt_auth import CookieJWTAuthentication
from rest_framework.response import Response
from utils.custom_paginator import CustomPaginator
from django.http import HttpResponse, JsonResponse
from ...models import WorkItems
from ..serializers.work_items_serializer import WorkItemsSerializer, WorkItemsWriteSerializer
from django_filters.rest_framework import DjangoFilterBackend
from ...permission import WorkItemAccessPermission
from django.db.models import Q

class WorkItemsViewset(viewsets.ModelViewSet):
    queryset = WorkItems.objects.all().order_by("-id")
    serializer_class = WorkItemsSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated, WorkItemAccessPermission]
    pagination_class = CustomPaginator

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["project", "status", "priority", "assigned_to"]
    search_fields = ["title", "description"]
    ordering_fields = ["due_date", "created_at", "updated_at", "priority", "title"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user

        active = ActiveClient.objects.select_related("client").filter(user=user).first()
        if not active:
            return WorkItems.objects.none()

        role = (
            UserClientRole.objects
            .filter(user=user, client=active.client)
            .values_list("role", flat=True)
            .first()
        )
        if not role:
            return WorkItems.objects.none()

        qs = WorkItems.objects.all()

        if role in ("member", "viewer"):
            qs = qs.filter(
                Q(project__projectmembers__user=user) | Q(assigned_to=user)
            )

        # Performance: avoid N+1
        qs = qs.select_related("project").prefetch_related(
            "assigned_to",
            "project__projectmembers_set__user",
            "project__projectmembers_set__user__profile",
        )

        return qs.distinct().order_by("-id")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return WorkItemsWriteSerializer
        return WorkItemsSerializer

    @extend_schema(
        request=WorkItemsWriteSerializer,
        responses={201: WorkItemsSerializer}
    )
    def create(self, request, *args, **kwargs):
        # Use write serializer for validation and saving
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        
        # Use read serializer for response to include all fields
        read_serializer = WorkItemsSerializer(instance)
        headers = self.get_success_headers(read_serializer.data)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Use write serializer for validation and saving
        write_serializer = self.get_serializer(instance, data=request.data, partial=partial)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        
        # Use read serializer for response to include all fields
        read_serializer = WorkItemsSerializer(instance)
        return Response(read_serializer.data)

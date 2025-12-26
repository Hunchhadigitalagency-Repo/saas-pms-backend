from backend.work_items.models import WorkItems
from project.permission import ProjectAccessPermission
from customer.models import ActiveClient, UserClientRole
from project.models import Project, ProjectActivityLog
from rest_framework import viewsets, filters
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from project.adapters.serializers.project_serializer import ProjectSerializer, OnGoingProjectSerializer, ProjectWriteSerializer
from project.adapters.serializers.project_activity_log_serializer import ProjectActivityLogSerializer
from utils.custom_paginator import CustomPaginator
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from pms.jwt_auth import CookieJWTAuthentication
import json
import logging

logger = logging.getLogger(__name__)

class ProjectViewSet(viewsets.ModelViewSet):
    """
    Projects API with:
    - cookie JWT auth
    - list filtering/search/ordering
    - role-based scoping in get_queryset()
    - object-level permissions via ProjectAccessPermission
    - read/write serializer switching
    """
    serializer_class = ProjectSerializer
    pagination_class = CustomPaginator
    permission_classes = [IsAuthenticated, ProjectAccessPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "priority"]
    search_fields = ["name", "description"]
    ordering_fields = ["due_date", "created_at", "priority"]
    authentication_classes = [CookieJWTAuthentication]

    def get_queryset(self):
        user = self.request.user

        active = ActiveClient.objects.select_related("client").filter(user=user).first()
        if not active:
            return Project.objects.none()

        role = (
            UserClientRole.objects.filter(user=user, client=active.client)
            .values_list("role", flat=True)
            .first()
        )

        # No role => no access
        if not role:
            return Project.objects.none()

        qs = Project.objects.all()

        if role in ("member", "viewer"):
            qs = qs.filter(projectmembers__user=user)

        # Performance (optional but recommended if you return team_members frequently)
        qs = qs.prefetch_related(
            "projectmembers_set__user",
            "projectmembers_set__user__profile",  # adjust if your related_name differs
        )

        return qs.distinct().order_by("-id")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ProjectWriteSerializer
        return ProjectSerializer

    def create(self, request, *args, **kwargs):
        # Use write serializer for validation and saving
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        
        # Use read serializer for response to include team_members and all fields
        read_serializer = ProjectSerializer(instance)
        headers = self.get_success_headers(read_serializer.data)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Use write serializer for validation and saving
        write_serializer = self.get_serializer(instance, data=request.data, partial=partial)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        
        # Use read serializer for response to include team_members and all fields
        read_serializer = ProjectSerializer(instance)
        return Response(read_serializer.data)

class OngoingProjectViewSet(viewsets.ModelViewSet):
    """
    Ongoing projects (status='active') with role-based scoping.
    Mirrors `ProjectViewSet` access rules so member/viewer roles only see assigned projects.
    """
    serializer_class = OnGoingProjectSerializer
    pagination_class = None
    permission_classes = [IsAuthenticated, ProjectAccessPermission]
    authentication_classes = [CookieJWTAuthentication]

    def get_queryset(self):
        user = self.request.user

        active = ActiveClient.objects.select_related("client").filter(user=user).first()
        if not active:
            return Project.objects.none()

        role = (
            UserClientRole.objects.filter(user=user, client=active.client)
            .values_list("role", flat=True)
            .first()
        )

        if not role:
            return Project.objects.none()

        qs = Project.objects.filter(status="active")

        if role in ("member", "viewer"):
            qs = qs.filter(projectmembers__user=user)

        qs = qs.prefetch_related(
            "projectmembers_set__user",
            "projectmembers_set__user__profile",
        )

        return qs.distinct().order_by("-id")


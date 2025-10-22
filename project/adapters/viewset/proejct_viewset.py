from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from project.models import Project
from project.adapters.serializers.project_serializer import ProjectSerializer, OnGoingProjectSerializer
from utils.custom_paginator import CustomPaginator


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().order_by('-id')
    serializer_class = ProjectSerializer
    pagination_class = CustomPaginator

    # 👇 Add this
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # fields you can filter by (exact match)
    filterset_fields = ['status', 'priority']

    # fields you can search by (partial match)
    search_fields = ['name', 'description']

    # optional ordering fields
    ordering_fields = ['due_date', 'created_at', 'priority']

class OngoingProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.filter(status='active').order_by('-id')
    serializer_class = OnGoingProjectSerializer
    pagination_class = None
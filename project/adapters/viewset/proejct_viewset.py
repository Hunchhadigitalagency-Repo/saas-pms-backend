from rest_framework import viewsets, filters
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from project.models import Project
from project.adapters.serializers.project_serializer import ProjectSerializer, OnGoingProjectSerializer, ProjectWriteSerializer
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

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
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
    queryset = Project.objects.filter(status='active').order_by('-id')
    serializer_class = OnGoingProjectSerializer
    pagination_class = None
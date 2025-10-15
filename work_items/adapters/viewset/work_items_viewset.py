from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, filters
from utils.custom_paginator import CustomPaginator
from django.http import HttpResponse, JsonResponse
from ...models import WorkItems
from ..serializers.work_items_serializer import WorkItemsSerializer, WorkItemsWriteSerializer
from django_filters.rest_framework import DjangoFilterBackend

class WorkItemsViewset(viewsets.ModelViewSet):
    queryset = WorkItems.objects.all().order_by('id')
    serializer_class = WorkItemsSerializer
    pagination_class = CustomPaginator

    # 👇 Add filtering, searching and ordering
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Fields you can filter by (exact match)
    filterset_fields = ['project', 'status', 'priority', 'assigned_to']

    # Fields you can search by (partial match)
    search_fields = ['title', 'description']

    # Optional ordering fields
    ordering_fields = ['due_date', 'created_at', 'updated_at', 'priority', 'title']

    # Default ordering
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return WorkItemsWriteSerializer
        return WorkItemsSerializer

    @extend_schema(
        request=WorkItemsWriteSerializer,
        responses={201: WorkItemsSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

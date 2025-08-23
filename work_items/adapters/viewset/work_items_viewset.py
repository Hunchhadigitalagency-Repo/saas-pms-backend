from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from utils.custom_paginator import CustomPaginator
from django.http import HttpResponse, JsonResponse
from ...models import WorkItems
from ..serializers.work_items_serializer import WorkItemsSerializer, WorkItemsWriteSerializer

class WorkItemsViewset(viewsets.ModelViewSet):
    queryset = WorkItems.objects.all().order_by('id')
    serializer_class = WorkItemsSerializer
    pagination_class = CustomPaginator

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

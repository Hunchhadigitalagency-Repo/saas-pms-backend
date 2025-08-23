from rest_framework import viewsets
from utils.custom_paginator import CustomPaginator
from django.http import HttpResponse, JsonResponse
from ...models import WorkItems
from ..serializers.work_items_serializer import WorkItemsSerializer

class WorkItemsViewset(viewsets.ModelViewSet):
    queryset = WorkItems.objects.all().order_by('id')
    serializer_class = WorkItemsSerializer
    pagination_class = CustomPaginator



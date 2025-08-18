from rest_framework import viewsets
from task.models import Task
from task.adapters.serializers.task_serializer import TaskSerializer
from utils.custom_paginator import CustomPaginator
from django.http import HttpResponse, JsonResponse

class TaskViewset(viewsets.ModelViewSet):
    queryset = Task.objects.all().order_by('id')
    serializer_class = TaskSerializer
    pagination_class = CustomPaginator



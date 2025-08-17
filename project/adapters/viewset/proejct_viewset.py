from rest_framework import viewsets
from project.models import Project
from project.adapters.serializers.project_serializer import ProjectSerializer
from utils.custom_paginator import CustomPaginator
from django.http import HttpResponse, JsonResponse

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().order_by('id')
    serializer_class = ProjectSerializer
    pagination_class = CustomPaginator



from django.urls import path, include
from rest_framework.routers import DefaultRouter
from project.adapters.viewset.proejct_viewset import ProjectViewSet, OngoingProjectViewSet, ProjectActivityLogViewSet


router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'ongoing-projects', OngoingProjectViewSet, basename='ongoing-project')
router.register(r'project-activity-logs', ProjectActivityLogViewSet, basename='project-activity-log')

urlpatterns = [
    path('', include(router.urls)),
]

from django.urls import path, include
from project.adapters.viewset.project_activity_viewset import ProjectActivityLogViewSet
from project.adapters.viewset.project_slack_channel_viewset import ProjectSlackChannelViewSet
from rest_framework.routers import DefaultRouter
from project.adapters.viewset.proejct_viewset import ProjectViewSet, OngoingProjectViewSet


router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'ongoing-projects', OngoingProjectViewSet, basename='ongoing-project')
router.register(r'project-activity-logs', ProjectActivityLogViewSet, basename='project-activity-log')
router.register(r'project-slack-channels', ProjectSlackChannelViewSet, basename='project-slack-channel')

urlpatterns = [
    path('', include(router.urls)),
]

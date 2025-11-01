from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .adapters.viewsets.dashbaord_count_card_viewset import DashboardViewset
from .adapters.viewsets.dashboard_project_status_viewset import WorkItemStatusDistribution, WorkItemPriorityDistribution

router = DefaultRouter()
router.register(r'dashboard', DashboardViewset, basename='project')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/work-item-status-distribution/', WorkItemStatusDistribution.as_view(), name='work-item-status-distribution'),
    path('dashboard/work-item-priority-distribution/', WorkItemPriorityDistribution.as_view(), name='work-item-priority-distribution'),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .adapters.viewsets.dashbaord_count_card_viewset import DashboardViewset
from .adapters.viewsets.dashboard_project_status_viewset import (
    WorkItemStatusDistribution, 
    WorkItemPriorityDistribution,
)
from .adapters.viewsets.dashboard_due_work_items_viewset import DueTasksView  # Import the new view

router = DefaultRouter()
router.register(r'dashboard', DashboardViewset, basename='project')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', include([
        path('', include(router.urls)),
        path('work-item-status-distribution/', WorkItemStatusDistribution.as_view(), name='work-item-status-distribution'),
        path('work-item-priority-distribution/', WorkItemPriorityDistribution.as_view(), name='work-item-priority-distribution'),
        path('due-tasks/', DueTasksView.as_view(), name='due-tasks'),
    ])),
]

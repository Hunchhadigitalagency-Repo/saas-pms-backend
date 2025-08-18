from django.urls import path, include
from rest_framework.routers import DefaultRouter
from task.adapters.viewset.task_viewset import TaskViewset

router = DefaultRouter()
router.register(r'tasks', TaskViewset)

urlpatterns = [
    path('', include(router.urls)),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from project.adapters.viewset.proejct_viewset import ProjectViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

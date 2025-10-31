from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .adapters.viewsets.dashbaord_viewset import DashboardViewset



router = DefaultRouter()
router.register(r'dashboard', DashboardViewset, basename='project')


urlpatterns = [
    path('', include(router.urls)),
]

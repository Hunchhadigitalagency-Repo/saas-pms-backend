from django.urls import path, include
from rest_framework.routers import DefaultRouter
from work_items.adapters.viewset.work_items_viewset import WorkItemsViewset

router = DefaultRouter()
router.register(r'work-items', WorkItemsViewset)

urlpatterns = [
    path('', include(router.urls)),
]

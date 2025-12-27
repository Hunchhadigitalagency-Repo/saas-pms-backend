from rest_framework.routers import DefaultRouter
from settings.adapters.viewsets import SlackTokenViewSet

router = DefaultRouter()
router.register(r'slack', SlackTokenViewSet, basename='slack-token')

urlpatterns = router.urls

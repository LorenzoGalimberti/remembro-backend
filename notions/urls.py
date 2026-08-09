from rest_framework.routers import DefaultRouter
from .views import NotionViewSet

router = DefaultRouter()
router.register('', NotionViewSet, basename='notion')

urlpatterns = router.urls
